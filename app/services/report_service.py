import io
import base64
import logging
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, date, timedelta, timezone
from typing import Dict, List, Optional, Any
from app.config.database import supabase_admin
from app.schemas.report import ReportType, ReportStatus, BiomarkerStat, ReportSummary
from app.utils.pdf_generator import generate_pdf
from app.utils.s3 import S3Service

logger = logging.getLogger(__name__)

# Normal ranges for each biomarker (min_normal, max_normal, unit)
BIOMARKER_NORMAL = {
    "heart_rate":              (60,  100,  "bpm"),
    "blood_pressure_systolic": (90,  120,  "mmHg"),
    "blood_pressure_diastolic":(60,  80,   "mmHg"),
    "glucose":                 (70,  100,  "mg/dL"),
    "steps":                   (7000, 15000, "steps"),
    "sleep":                   (7,   9,    "hrs"),
}

BIOMARKER_LABELS = {
    "heart_rate":               "Heart Rate",
    "blood_pressure_systolic":  "Blood Pressure (Systolic)",
    "blood_pressure_diastolic": "Blood Pressure (Diastolic)",
    "glucose":                  "Blood Glucose",
    "steps":                    "Daily Steps",
    "sleep":                    "Sleep",
}

PULSE_BLUE  = "#2563eb"
PULSE_GREEN = "#16a34a"
PULSE_RED   = "#dc2626"
PULSE_AMBER = "#d97706"
PULSE_GRAY  = "#6b7280"


class ReportService:

    # ── Create report record ────────────────────────────────────────────────────
    @staticmethod
    async def create_report(
        patient_user_id: str,
        report_type: str,
        date_from: date,
        date_to: date,
        biomarker_types: Optional[List[str]] = None,
    ) -> Dict:
        record = {
            "patient_user_id": patient_user_id,
            "report_type":     report_type,
            "date_from":       date_from.isoformat(),
            "date_to":         date_to.isoformat(),
            "biomarker_types": biomarker_types,
            "status":          ReportStatus.PENDING,
        }
        res = supabase_admin.table("reports").insert(record).execute()
        return res.data[0]

    # ── List reports for a patient ──────────────────────────────────────────────
    @staticmethod
    async def list_reports(patient_user_id: str, limit: int = 20) -> List[Dict]:
        res = (
            supabase_admin.table("reports")
            .select("*")
            .eq("patient_user_id", patient_user_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return res.data or []

    # ── Get single report ───────────────────────────────────────────────────────
    @staticmethod
    async def get_report(report_id: str, patient_user_id: str) -> Optional[Dict]:
        res = (
            supabase_admin.table("reports")
            .select("*")
            .eq("id", report_id)
            .eq("patient_user_id", patient_user_id)
            .execute()
        )
        return res.data[0] if res.data else None

    # ── Fetch biomarker data ────────────────────────────────────────────────────
    @staticmethod
    async def _fetch_biomarkers(
        patient_user_id: str,
        date_from: date,
        date_to: date,
        biomarker_types: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        query = (
            supabase_admin.table("biomarkers")
            .select("biomarker_type, value, unit, recorded_at")
            .eq("user_id", patient_user_id)
            .gte("recorded_at", f"{date_from}T00:00:00")
            .lte("recorded_at", f"{date_to}T23:59:59")
            .order("recorded_at")
        )
        if biomarker_types:
            query = query.in_("biomarker_type", biomarker_types)

        res = query.execute()
        if not res.data:
            return pd.DataFrame(columns=["biomarker_type", "value", "unit", "recorded_at"])

        df = pd.DataFrame(res.data)
        df["recorded_at"] = pd.to_datetime(df["recorded_at"], format="ISO8601", utc=True)
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        return df

    # ── Fetch health scores ─────────────────────────────────────────────────────
    @staticmethod
    async def _fetch_scores(patient_user_id: str, date_from: date, date_to: date) -> pd.DataFrame:
        try:
            res = (
                supabase_admin.table("daily_health_scores")
                .select("date, score")
                .eq("user_id", patient_user_id)
                .gte("date", date_from.isoformat())
                .lte("date", date_to.isoformat())
                .order("date")
                .execute()
            )
            if not res.data:
                return pd.DataFrame(columns=["score_date", "total_score"])
            df = pd.DataFrame(res.data)
            df = df.rename(columns={"date": "score_date", "score": "total_score"})
            df["total_score"] = pd.to_numeric(df["total_score"], errors="coerce")
            return df
        except Exception as e:
            logger.warning(f"Could not fetch health scores (table may not exist yet): {e}")
            return pd.DataFrame(columns=["score_date", "total_score"])

    # ── Fetch patient info ──────────────────────────────────────────────────────
    @staticmethod
    async def _fetch_patient_info(patient_user_id: str) -> Dict:
        user_res = (
            supabase_admin.table("users")
            .select("email")
            .eq("id", patient_user_id)
            .execute()
        )
        patient_res = (
            supabase_admin.table("patients")
            .select("full_name")
            .eq("user_id", patient_user_id)
            .execute()
        )
        email     = user_res.data[0]["email"] if user_res.data else ""
        full_name = patient_res.data[0]["full_name"] if patient_res.data else "Patient"
        return {"full_name": full_name, "email": email}

    # ── Fetch goal completions ──────────────────────────────────────────────────
    @staticmethod
    async def _fetch_goals(patient_user_id: str, date_from: date, date_to: date) -> List[Dict]:
        try:
            res = (
                supabase_admin.table("goal_completions")
                .select("goal_text, goal_frequency, completion_date, status")
                .eq("user_id", patient_user_id)
                .gte("completion_date", date_from.isoformat())
                .lte("completion_date", date_to.isoformat())
                .order("completion_date")
                .execute()
            )
            return res.data or []
        except Exception as e:
            logger.warning(f"Could not fetch goals: {e}")
            return []

    # ── Fetch pet profile + state events ────────────────────────────────────
    @staticmethod
    async def _fetch_pet_profile(patient_user_id: str, date_from: date, date_to: date) -> Dict:
        try:
            pet_resp = (
                supabase_admin.table("patient_pet_profiles")
                .select("current_emotion, current_score, pet_name, pet_catalog_id, accessory_unlocked")
                .eq("patient_user_id", patient_user_id)
                .limit(1)
                .execute()
            )
            if not pet_resp.data:
                return {}
            pet = pet_resp.data[0]

            cat_resp = (
                supabase_admin.table("pet_catalog")
                .select("pet_key, display_name")
                .eq("id", pet["pet_catalog_id"])
                .limit(1)
                .execute()
            )
            cat = cat_resp.data[0] if cat_resp.data else {}

            events_resp = (
                supabase_admin.table("patient_pet_state_events")
                .select("*")
                .eq("patient_user_id", patient_user_id)
                .gte("created_at", f"{date_from}T00:00:00")
                .lte("created_at", f"{date_to}T23:59:59")
                .eq("trigger_source", "health_summary_updated")
                .order("created_at")
                .execute()
            )
            return {
                **pet,
                "pet_key":      cat.get("pet_key", ""),
                "display_name": cat.get("display_name", "Pet"),
                "events":       events_resp.data or [],
            }
        except Exception as e:
            logger.warning(f"Could not fetch pet profile: {e}")
            return {}

    # ── Build pet mood timeline chart ────────────────────────────────────────
    @staticmethod
    def _make_pet_chart(pet_info: Dict, score_df: "pd.DataFrame") -> Optional[str]:
        events = [e for e in pet_info.get("events", [])
                  if e.get("previous_emotion") != e.get("new_emotion")]
        if score_df.empty and not events:
            return None

        fig, ax = plt.subplots(figsize=(10, 3.5), dpi=120)
        fig.patch.set_facecolor("#f9fafb")
        ax.set_facecolor("#f9fafb")

        # Emotion zone background bands
        ax.axhspan(70, 105, alpha=0.08, color=PULSE_GREEN)
        ax.axhspan(40, 70,  alpha=0.08, color=PULSE_AMBER)
        ax.axhspan(0,  40,  alpha=0.08, color=PULSE_BLUE)

        # Zone edge lines
        ax.axhline(70, color=PULSE_GREEN, linestyle=":", linewidth=0.8, alpha=0.6)
        ax.axhline(40, color=PULSE_BLUE,  linestyle=":", linewidth=0.8, alpha=0.6)

        # Score line
        if not score_df.empty:
            sc_dates = pd.to_datetime(score_df["score_date"])
            ax.plot(sc_dates, score_df["total_score"],
                    color=PULSE_BLUE, linewidth=2.5, marker="o", markersize=4, zorder=3)
            ax.fill_between(sc_dates, score_df["total_score"], alpha=0.1, color=PULSE_BLUE)

        # State-change vertical markers
        emo_colors = {"happy": PULSE_GREEN, "neutral": PULSE_AMBER, "sad": PULSE_RED}
        for event in events:
            try:
                dt  = pd.to_datetime(event["created_at"])
                new = event.get("new_emotion", "neutral")
                sc  = float(event.get("final_score", 50))
                c   = emo_colors.get(new, PULSE_GRAY)
                ax.axvline(x=dt, color=c, linestyle="--", linewidth=1.5, alpha=0.65, zorder=2)
                ax.annotate(
                    f"→ {new.title()}",
                    xy=(dt, min(sc + 6, 98)),
                    fontsize=7.5, color=c, fontweight="bold",
                    ha="center", va="bottom",
                )
            except Exception:
                pass

        # Zone labels (right y-axis side)
        ax.text(1.01, 85, "Happy",   fontsize=7.5, color=PULSE_GREEN, fontweight="bold",
                transform=ax.get_yaxis_transform(), va="center")
        ax.text(1.01, 55, "Neutral", fontsize=7.5, color=PULSE_AMBER, fontweight="bold",
                transform=ax.get_yaxis_transform(), va="center")
        ax.text(1.01, 20, "Sad",     fontsize=7.5, color=PULSE_BLUE,  fontweight="bold",
                transform=ax.get_yaxis_transform(), va="center")

        pet_label = pet_info.get("pet_name") or pet_info.get("display_name", "Pet")
        ax.set_ylim(0, 105)
        ax.set_ylabel("Health Score", fontsize=8, color=PULSE_GRAY)
        ax.set_title(f"{pet_label}'s Mood Journey", fontsize=10,
                     fontweight="bold", color="#111827", pad=6)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
        ax.xaxis.set_major_locator(mdates.AutoDateLocator(maxticks=8))
        plt.setp(ax.get_xticklabels(), rotation=30, ha="right", fontsize=8)
        ax.tick_params(axis="y", labelsize=8)
        ax.spines[["top", "right"]].set_visible(False)
        ax.spines[["left", "bottom"]].set_color("#e5e7eb")
        plt.tight_layout(pad=0.5)

        buf = io.BytesIO()
        plt.savefig(buf, format="png", bbox_inches="tight", facecolor="#f9fafb")
        plt.close(fig)
        buf.seek(0)
        return base64.b64encode(buf.read()).decode()

    # ── Fetch AI recommendations ─────────────────────────────────────────────
    @staticmethod
    async def _fetch_recommendations(patient_user_id: str) -> List[Dict]:
        try:
            res = (
                supabase_admin.table("ai_recommendations")
                .select("category, title, description, priority, action_steps, related_goal, requires_professional_consultation")
                .eq("user_id", patient_user_id)
                .in_("status", ["active", "in_progress"])
                .order("priority")
                .limit(8)
                .execute()
            )
            return res.data or []
        except Exception as e:
            logger.warning(f"Could not fetch recommendations: {e}")
            return []

    # ── Compute per-biomarker stats ─────────────────────────────────────────────
    @staticmethod
    def _compute_stats(df: pd.DataFrame, date_from: date, date_to: date) -> List[BiomarkerStat]:
        stats = []
        all_types = list(BIOMARKER_NORMAL.keys())
        types_present = df["biomarker_type"].unique().tolist() if not df.empty else []
        # Only include types that have data or were requested
        for bt in all_types:
            sub = df[df["biomarker_type"] == bt] if not df.empty else pd.DataFrame()
            min_n, max_n, unit = BIOMARKER_NORMAL.get(bt, (None, None, ""))

            if sub.empty:
                stats.append(BiomarkerStat(
                    biomarker_type=bt, unit=unit,
                    avg=None, min=None, max=None, latest=None,
                    readings_count=0, days_in_normal=0,
                    days_total=(date_to - date_from).days + 1,
                    trend="insufficient_data", status="no_data"
                ))
                continue

            # Steps are always whole numbers; round(x, 0) returns float so use int()
            is_steps = (bt == "steps")
            def _r(v): return int(round(v)) if is_steps else round(v, 1)
            avg_val = _r(sub["value"].mean())
            min_val = _r(sub["value"].min())
            max_val = _r(sub["value"].max())
            latest  = _r(sub.sort_values("recorded_at").iloc[-1]["value"])
            count     = len(sub)
            days_total = (date_to - date_from).days + 1

            # Days in normal range
            if min_n is not None and max_n is not None:
                daily_avg = sub.groupby(sub["recorded_at"].dt.date)["value"].mean()
                days_in_normal = int(((daily_avg >= min_n) & (daily_avg <= max_n)).sum())
            else:
                days_in_normal = 0

            # Trend: compare first half vs second half
            mid = date_from + timedelta(days=(date_to - date_from).days // 2)
            first_half = sub[sub["recorded_at"].dt.date <= mid]["value"].mean()
            second_half = sub[sub["recorded_at"].dt.date > mid]["value"].mean()

            if pd.isna(first_half) or pd.isna(second_half):
                trend = "insufficient_data"
            else:
                diff_pct = (second_half - first_half) / max(abs(first_half), 1) * 100
                # For steps/sleep, higher is better; for others, closer to normal is better
                if bt in ("steps", "sleep"):
                    trend = "improving" if diff_pct > 5 else "declining" if diff_pct < -5 else "stable"
                else:
                    # Closer to midpoint of normal range = better
                    if min_n and max_n:
                        mid_n = (min_n + max_n) / 2
                        d1 = abs(first_half - mid_n)
                        d2 = abs(second_half - mid_n)
                        trend = "improving" if d2 < d1 * 0.95 else "declining" if d2 > d1 * 1.05 else "stable"
                    else:
                        trend = "stable"

            # Status
            if min_n is not None and max_n is not None:
                if min_n <= avg_val <= max_n:
                    status = "normal"
                elif (min_n * 0.9 <= avg_val <= max_n * 1.1):
                    status = "borderline"
                else:
                    status = "abnormal"
            else:
                status = "normal"

            stats.append(BiomarkerStat(
                biomarker_type=bt, unit=unit,
                avg=avg_val, min=min_val, max=max_val, latest=latest,
                readings_count=count, days_in_normal=days_in_normal,
                days_total=days_total, trend=trend, status=status,
            ))
        return stats

    # ── Generate matplotlib chart as base64 PNG ─────────────────────────────────
    @staticmethod
    def _make_chart(df: pd.DataFrame, biomarker_type: str) -> Optional[str]:
        sub = df[df["biomarker_type"] == biomarker_type].copy()
        if sub.empty or len(sub) < 2:
            return None

        min_n, max_n, unit = BIOMARKER_NORMAL.get(biomarker_type, (None, None, ""))
        label = BIOMARKER_LABELS.get(biomarker_type, biomarker_type.replace("_", " ").title())

        fig, ax = plt.subplots(figsize=(8, 3), dpi=120)
        fig.patch.set_facecolor("#f9fafb")
        ax.set_facecolor("#f9fafb")

        # Daily average
        sub["date"] = sub["recorded_at"].dt.date
        daily = sub.groupby("date")["value"].mean().reset_index()
        daily["date"] = pd.to_datetime(daily["date"])

        ax.plot(daily["date"], daily["value"],
                color=PULSE_BLUE, linewidth=2, marker="o", markersize=4, zorder=3)
        ax.fill_between(daily["date"], daily["value"], alpha=0.08, color=PULSE_BLUE)

        # Normal range band
        if min_n is not None and max_n is not None:
            ax.axhspan(min_n, max_n, alpha=0.12, color=PULSE_GREEN, label=f"Normal ({min_n}–{max_n} {unit})")

        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
        ax.xaxis.set_major_locator(mdates.AutoDateLocator(maxticks=8))
        plt.setp(ax.get_xticklabels(), rotation=30, ha="right", fontsize=8)
        ax.tick_params(axis="y", labelsize=8)
        ax.set_ylabel(unit, fontsize=8, color=PULSE_GRAY)
        ax.set_title(label, fontsize=10, fontweight="bold", color="#111827", pad=6)
        ax.spines[["top", "right"]].set_visible(False)
        ax.spines[["left", "bottom"]].set_color("#e5e7eb")
        ax.tick_params(colors=PULSE_GRAY)
        if min_n is not None:
            ax.legend(fontsize=7, loc="upper right", framealpha=0.7)

        plt.tight_layout(pad=0.5)
        buf = io.BytesIO()
        plt.savefig(buf, format="png", bbox_inches="tight", facecolor="#f9fafb")
        plt.close(fig)
        buf.seek(0)
        return base64.b64encode(buf.read()).decode()

    # ── Generate CSV ────────────────────────────────────────────────────────────
    @staticmethod
    async def generate_csv(df: pd.DataFrame) -> bytes:
        if df.empty:
            return b"biomarker_type,value,unit,recorded_at\n"
        out = df[["biomarker_type", "value", "unit", "recorded_at"]].copy()
        out["recorded_at"] = out["recorded_at"].astype(str)
        return out.to_csv(index=False).encode()

    # ── Main generation entry point (runs in background) ───────────────────────
    @staticmethod
    async def generate_report(report_id: str, patient_user_id: str):
        try:
            # Mark as generating
            supabase_admin.table("reports").update(
                {"status": ReportStatus.GENERATING}
            ).eq("id", report_id).execute()

            # Fetch report record
            rec = supabase_admin.table("reports").select("*").eq("id", report_id).execute()
            if not rec.data:
                return
            report = rec.data[0]

            date_from = date.fromisoformat(report["date_from"])
            date_to   = date.fromisoformat(report["date_to"])
            bt_filter = report.get("biomarker_types")

            # Fetch all data
            patient      = await ReportService._fetch_patient_info(patient_user_id)
            df           = await ReportService._fetch_biomarkers(patient_user_id, date_from, date_to, bt_filter)
            score_df     = await ReportService._fetch_scores(patient_user_id, date_from, date_to)
            goals        = await ReportService._fetch_goals(patient_user_id, date_from, date_to)
            recs         = await ReportService._fetch_recommendations(patient_user_id)
            pet_info     = await ReportService._fetch_pet_profile(patient_user_id, date_from, date_to)

            # Compute stats
            stats = ReportService._compute_stats(df, date_from, date_to)

            # Score summary
            avg_score  = round(score_df["total_score"].mean(), 1) if not score_df.empty else None
            best_score = round(score_df["total_score"].max(), 1) if not score_df.empty else None
            worst_score = round(score_df["total_score"].min(), 1) if not score_df.empty else None

            if not score_df.empty and len(score_df) >= 2:
                mid = len(score_df) // 2
                s1 = score_df.iloc[:mid]["total_score"].mean()
                s2 = score_df.iloc[mid:]["total_score"].mean()
                score_trend = "improving" if s2 > s1 + 2 else "declining" if s2 < s1 - 2 else "stable"
            else:
                score_trend = "insufficient_data"

            # Goal stats
            total_goals     = len(goals)
            completed_goals = sum(1 for g in goals if g["status"] == "completed")
            goal_rate       = round(completed_goals / total_goals * 100, 1) if total_goals > 0 else None

            summary = {
                "avg_health_score":      avg_score,
                "best_score":            best_score,
                "worst_score":           worst_score,
                "score_trend":           score_trend,
                "total_readings":        len(df),
                "biomarker_stats":       [s.model_dump() for s in stats],
                "goals_total":           total_goals,
                "goals_completed":       completed_goals,
                "goals_completion_rate": goal_rate,
                "recommendations":       recs,
            }

            # Generate charts (base64 PNGs)
            charts = {}
            for bt in BIOMARKER_NORMAL.keys():
                chart = ReportService._make_chart(df, bt)
                if chart:
                    charts[bt] = chart

            # Score chart
            score_chart = None
            if not score_df.empty and len(score_df) >= 2:
                fig, ax = plt.subplots(figsize=(10, 3), dpi=120)
                fig.patch.set_facecolor("#f9fafb")
                ax.set_facecolor("#f9fafb")
                sc_dates = pd.to_datetime(score_df["score_date"])
                ax.fill_between(sc_dates, score_df["total_score"], alpha=0.15, color=PULSE_BLUE)
                ax.plot(sc_dates, score_df["total_score"], color=PULSE_BLUE, linewidth=2, marker="o", markersize=4)
                ax.axhline(70, color=PULSE_GREEN, linestyle="--", linewidth=1, alpha=0.6, label="Happy threshold (70)")
                ax.axhline(40, color=PULSE_AMBER, linestyle="--", linewidth=1, alpha=0.6, label="Sad threshold (40)")
                ax.set_ylim(0, 105)
                ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
                ax.xaxis.set_major_locator(mdates.AutoDateLocator(maxticks=10))
                plt.setp(ax.get_xticklabels(), rotation=30, ha="right", fontsize=8)
                ax.tick_params(axis="y", labelsize=8)
                ax.set_ylabel("Score", fontsize=8, color=PULSE_GRAY)
                ax.set_title("Daily Health Score", fontsize=10, fontweight="bold", color="#111827", pad=6)
                ax.spines[["top", "right"]].set_visible(False)
                ax.legend(fontsize=7, loc="upper right", framealpha=0.7)
                plt.tight_layout(pad=0.5)
                buf = io.BytesIO()
                plt.savefig(buf, format="png", bbox_inches="tight", facecolor="#f9fafb")
                plt.close(fig)
                buf.seek(0)
                score_chart = base64.b64encode(buf.read()).decode()

            # Pet timeline chart
            pet_chart = ReportService._make_pet_chart(pet_info, score_df) if pet_info else None

            # Build PDF
            pdf_bytes = await generate_pdf(
                patient_name=patient.get("full_name", "Patient"),
                report_type=report["report_type"],
                date_from=date_from,
                date_to=date_to,
                summary=summary,
                stats=stats,
                charts=charts,
                score_chart=score_chart,
                goals=goals,
                recommendations=recs,
                pet_info=pet_info or None,
                pet_chart=pet_chart,
            )

            # Build CSV
            csv_bytes = await ReportService.generate_csv(df)

            # Upload both to S3
            s3 = S3Service()
            report_name = f"{report['report_type']}_{date_from}_{date_to}"

            pdf_result = await s3.upload_file(
                file_content=pdf_bytes,
                file_name=f"{report_name}.pdf",
                folder=f"pulse-hw-reports/{patient_user_id}",
                content_type="application/pdf",
            )
            csv_result = await s3.upload_file(
                file_content=csv_bytes,
                file_name=f"{report_name}.csv",
                folder=f"pulse-hw-reports/{patient_user_id}",
                content_type="text/csv",
            )

            supabase_admin.table("reports").update({
                "status":       ReportStatus.READY,
                "pdf_url":      pdf_result["file_key"],
                "csv_url":      csv_result["file_key"],
                "summary":      summary,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }).eq("id", report_id).execute()

            logger.info(f"Report {report_id} generated successfully")

        except Exception as e:
            logger.error(f"Report generation failed for {report_id}: {e}")
            supabase_admin.table("reports").update(
                {"status": ReportStatus.FAILED}
            ).eq("id", report_id).execute()

    # ── Preview: return JSON data for in-app charts (no file) ──────────────────
    @staticmethod
    async def get_preview_data(
        patient_user_id: str,
        date_from: date,
        date_to: date,
        biomarker_types: Optional[List[str]] = None,
    ) -> Dict:
        df       = await ReportService._fetch_biomarkers(patient_user_id, date_from, date_to, biomarker_types)
        score_df = await ReportService._fetch_scores(patient_user_id, date_from, date_to)
        goals    = await ReportService._fetch_goals(patient_user_id, date_from, date_to)
        recs     = await ReportService._fetch_recommendations(patient_user_id)
        stats    = ReportService._compute_stats(df, date_from, date_to)

        # Time series per biomarker for recharts
        series: Dict[str, List[Dict]] = {}
        if not df.empty:
            for bt in df["biomarker_type"].unique():
                sub = df[df["biomarker_type"] == bt].copy()
                sub["date"] = sub["recorded_at"].dt.date.astype(str)
                daily = sub.groupby("date")["value"].mean().reset_index()
                series[bt] = [
                    {"date": r["date"], "value": int(round(r["value"])) if bt == "steps" else round(r["value"], 1)}
                    for _, r in daily.iterrows()
                ]

        score_series = []
        if not score_df.empty:
            score_series = [
                {"date": r["score_date"], "score": r["total_score"]}
                for _, r in score_df.iterrows()
            ]

        # Goal stats
        total_goals     = len(goals)
        completed_goals = sum(1 for g in goals if g["status"] == "completed")
        goal_rate       = round(completed_goals / total_goals * 100, 1) if total_goals > 0 else None

        return {
            "stats":                 [s.model_dump() for s in stats],
            "series":                series,
            "score_series":          score_series,
            "normals":               {k: {"min": v[0], "max": v[1], "unit": v[2]} for k, v in BIOMARKER_NORMAL.items()},
            "goals":                 goals,
            "goals_total":           total_goals,
            "goals_completed":       completed_goals,
            "goals_completion_rate": goal_rate,
            "recommendations":       recs,
        }
