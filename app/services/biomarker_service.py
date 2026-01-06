import random
from app.config.database import supabase_admin
from fastapi import HTTPException, status
from typing import Dict, Optional, List
from datetime import datetime, timedelta, timezone
import logging
from app.schemas.biomarker import BiomarkerType

logger = logging.getLogger(__name__)


class BiomarkerService:
    """Service layer for biomarker data management"""

    @staticmethod
    async def insert_biomarker_data(
        user_id: str,
        biomarker_type: str,
        value: float,
        unit: str,
        source: str = "manual",
        device_id: Optional[str] = None,
        recorded_at: Optional[datetime] = None,
        notes: Optional[str] = None
    ) -> Dict:
        """
        Insert biomarker data (from device or manual entry)

        Business Rules:
        - If source is 'device', device_id must be provided and belong to user
        - If source is 'manual', device_id should be None
        - recorded_at defaults to current timestamp if not provided
        - Validate biomarker_type is one of the supported types
        - Validate value is within reasonable range (optional validation)

        Args:
            user_id: The user's ID
            biomarker_type: Type of biomarker (heart_rate, glucose, etc.)
            value: The biomarker value
            unit: Unit of measurement
            source: 'device' or 'manual'
            device_id: Device ID if source is 'device'
            recorded_at: When the reading was taken
            notes: Optional notes for manual entries

        Returns:
            Biomarker record

        TODO: Implement this function
        - Validate biomarker_type
        - If source is 'device', verify device_id belongs to user and is connected
        - Set recorded_at to now() if not provided
        - Insert biomarker data
        - Return created record
        """
        try:
            if biomarker_type not in [b.value for b in BiomarkerType]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, 
                    detail=f"Invalid biomarker_type '{biomarker_type}'." 
                )
            if source == "device":
                if not device_id:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="device_id must be provided when source is 'device'."
                    )
                # verify device belongs to user
                device_check = supabase_admin.table("devices").select("id, user_id, status").eq("id", device_id).eq("user_id", user_id).single().execute()
                if not device_check.data:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid device_id or device does not belong to user."
                    )
                if device_check.data["status"] != "connected":
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Device is not connected."
                    )
            else: #source is manual
                device_id = None  # ensure device_id is None for manual entries
                
            if not recorded_at:
                recorded_at = datetime.now(timezone.utc)
            
            # insert into biomarker table
            insert_data = {
                "user_id": user_id,
                "device_id": device_id,
                "biomarker_type": biomarker_type,
                "value": value,
                "unit": unit,
                "source": source,
                "recorded_at": recorded_at,
                "notes": notes
            }
            insert_response = supabase_admin.table("biomarkers").insert(insert_data).execute()
            if insert_response.error:
                logger.error(f"Error inserting biomarker data: {insert_response.error.message}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to insert biomarker data."
                )
            return insert_response.data[0]
        except HTTPException as he:
            raise he
        except Exception as e:
            logger.exception("Unexpected error inserting biomarker data")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred."
            )

    @staticmethod
    async def get_latest_biomarker_readings(user_id: str) -> Dict:
        """
        Get the latest reading for each biomarker type (for dashboard summary)

        Returns a dictionary with latest values for:
        - heart_rate
        - blood_pressure_systolic
        - blood_pressure_diastolic
        - glucose
        - steps
        - sleep

        Args:
            user_id: The user's ID

        Returns:
            Dictionary with latest biomarker readings and their status (normal/optimal/critical)

        TODO: Implement this function
        - For each biomarker type, get the most recent reading
        - Compare with biomarker_ranges to determine status
        - Return dashboard summary with all latest readings
        """
        try:
            latest_readings = {}
            biomarker_types = [b.value for b in BiomarkerType]
            for b_type in biomarker_types:
                response = supabase_admin.table("biomarkers")\
                    .select("*")\
                    .eq("user_id", user_id)\
                    .eq("biomarker_type", b_type)\
                    .order("recorded_at", desc=True)\
                    .limit(1)\
                    .execute()
                if response.data:
                    latest_readings[b_type] = response.data[0]
                else:
                    latest_readings[b_type] = None
            # compare with ranges to determine status
            ranges = ( supabase_admin.table("biomarker_ranges") .select("*") .execute() ).data 
            range_map = {r["biomarker_type"]: r for r in ranges}
            def compute_status(b_type, value):
                if b_type not in range_map:
                    return "unknown"
                r = range_map[b_type]
                if value < r["optimal_min"] or value > r["optimal_max"]:
                    return "critical"
                elif value < r["normal_min"] or value > r["normal_max"]:
                    return "normal"
                else:
                    return "optimal"
            dashboard_summary = {}
            for b_type, reading in latest_readings.items():
                if reading:
                    status = compute_status(b_type, reading["value"])
                    dashboard_summary[b_type] = {
                        "biomarker_type": b_type,
                        "value": reading["value"],
                        "unit": reading["unit"],
                        "recorded_at": reading["recorded_at"],
                        "source": reading["source"],
                        "status": status
                    }
                else:
                    dashboard_summary[b_type] = None
            return dashboard_summary
        except Exception as e:
            logger.exception("Unexpected error fetching latest biomarker readings")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred."
            )
            

    @staticmethod
    async def get_biomarker_history(
        user_id: str,
        biomarker_type: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict]:
        """
        Get historical biomarker data for a specific type

        Args:
            user_id: The user's ID
            biomarker_type: Type of biomarker to retrieve
            limit: Maximum number of records to return
            offset: Number of records to skip

        Returns:
            List of biomarker records, ordered by recorded_at DESC

        TODO: Implement this function
        - Query biomarkers table for user and type
        - Order by recorded_at DESC
        - Apply limit and offset for pagination
        - Return historical data
        """
        try:
            if biomarker_type not in [b.value for b in BiomarkerType]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, 
                    detail=f"Invalid biomarker_type '{biomarker_type}'." 
                )
            response = supabase_admin.table("biomarkers")\
                .select("*")\
                .eq("user_id", user_id)\
                .eq("biomarker_type", biomarker_type)\
                .order("recorded_at", desc=True)\
                .range(offset, offset + limit - 1) \
                .execute()
            if response.error:
                logger.error(f"Error fetching biomarker history: {response.error.message}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to fetch biomarker history."
                )
            return response.data
        except HTTPException as he:
            raise he
        except Exception as e:
            logger.exception("Unexpected error fetching biomarker history")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred."
            )

    @staticmethod
    async def get_all_biomarkers(
        user_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict]:
        """
        Get all biomarker data for a user (all types)

        Args:
            user_id: The user's ID
            limit: Maximum number of records to return
            offset: Number of records to skip

        Returns:
            List of all biomarker records, ordered by recorded_at DESC

        TODO: Implement this function
        - Query all biomarkers for user
        - Order by recorded_at DESC
        - Apply limit and offset
        - Return all biomarker data
        """
        try:
            response = supabase_admin.table("biomarkers")\
                .select("*")\
                .eq("user_id", user_id)\
                .order("recorded_at", desc=True)\
                .range(offset, offset + limit - 1) \
                .execute()
            if response.error:
                logger.error(f"Error fetching all biomarkers: {response.error.message}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to fetch biomarker data."
                )
            return response.data
        except HTTPException as he:
            raise he
        except Exception as e:
            logger.exception("Unexpected error fetching all biomarkers")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred."
            )   

    @staticmethod
    async def get_biomarker_ranges() -> List[Dict]:
        """
        Get reference ranges for all biomarker types

        Returns:
            List of biomarker reference ranges

        TODO: Implement this function
        - Query biomarker_ranges table
        - Return all reference ranges
        """
        try:
            response = supabase_admin.table("biomarker_ranges").select("*").execute()
            if response.error:
                logger.error(f"Error fetching biomarker ranges: {response.error.message}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to fetch biomarker ranges."
                )
            return response.data
        except Exception as e:
            logger.exception("Unexpected error fetching biomarker ranges")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred."
            )   

    @staticmethod
    async def get_patient_biomarkers_for_provider(
        provider_user_id: str,
        patient_user_id: str
    ) -> Dict:
        """
        Provider gets latest biomarker readings for a connected patient

        Business Rule: Provider must have an accepted connection with the patient

        Args:
            provider_user_id: The provider's user ID
            patient_user_id: The patient's user ID

        Returns:
            Patient's latest biomarker readings

        TODO: Implement this function
        - Verify provider has accepted connection with patient
        - Get latest biomarker readings for patient
        - Return dashboard summary
        """
        try:
            # verify connection
            connection_check = supabase_admin.table("patient_provider_connections")\
                .select("status")\
                .eq("provider_id", provider_user_id)\
                .eq("patient_id", patient_user_id)\
                .single()\
                .execute()
            if not connection_check.data or connection_check.data["status"] != "accepted":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No accepted connection with the patient."
                )
            # get patient's latest biomarker readings
            patient_biomarkers = await BiomarkerService.get_latest_biomarker_readings(patient_user_id)
            return patient_biomarkers
        except HTTPException as he:
            raise he
        except Exception as e:
            logger.exception("Unexpected error fetching patient biomarkers for provider")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred."
            )

    @staticmethod
    async def simulate_device_data(
        user_id: str,
        device_id: str,
        device_type: str,
        days_of_history: int = 7
    ) -> Dict:
        """
        Simulate realistic biomarker data for a connected device

        This is a simulation function for demo purposes. It generates:
        - Historical data for the past N days
        - Device-specific biomarkers only
        - Realistic values within healthy ranges
        - Random variation to mimic real readings
        - Multiple readings per day (spread throughout the day)

        Data Storage:
        - All generated readings are inserted into the 'biomarkers' table
        - Each record has:
          * user_id: The user who owns the device
          * device_id: The connected device
          * biomarker_type: Type of biomarker (heart_rate, steps, etc.)
          * value: Generated random value within healthy range
          * unit: Measurement unit (bpm, steps, hours, etc.)
          * source: Set to 'device' (not manual)
          * recorded_at: Timestamp spread across historical days
          * notes: NULL (device readings don't have notes)

        Device-Specific Biomarkers:
        - apple_watch: heart_rate, steps, sleep (1 sleep reading per day, 3-5 HR readings, 1 steps reading)
        - fitbit: heart_rate, steps, sleep (same as apple_watch)
        - whoop: heart_rate, sleep (3-5 HR readings, 1 sleep reading)
        - omron_bp: blood_pressure_systolic, blood_pressure_diastolic (2-3 readings per day, always paired)
        - freestyle_libre: glucose (8-12 readings per day - simulates CGM)

        Value Ranges (randomly generated within):
        - heart_rate: 60-85 bpm (resting)
        - blood_pressure_systolic: 110-125 mmHg
        - blood_pressure_diastolic: 70-80 mmHg
        - glucose: 80-110 mg/dL (fasting/normal)
        - steps: 5000-12000 steps per day
        - sleep: 6.5-8.5 hours per night

        Args:
            user_id: The user's ID
            device_id: The connected device ID
            device_type: Type of device (determines which biomarkers to generate)
            days_of_history: Number of days of historical data to generate (default: 7)

        Returns:
            Dictionary with:
            - total_readings: Total number of biomarker readings generated
            - biomarkers_generated: List of biomarker types generated
            - date_range: Start and end dates of generated data

        TODO: Implement this function
        - Get device type's supported_biomarkers from device_types table
        - For each day in the past N days:
          * Generate random values for each supported biomarker
          * Create realistic timestamps (spread throughout the day)
          * Insert into biomarkers table with source='device'
        - Return summary of generated data
        """
        try:
            # Fetch supported biomarkers for device type
            device_type_response = supabase_admin.table("device_types")\
                .select("supported_biomarkers")\
                .eq("device_type", device_type)\
                .single()\
                .execute()
            if not device_type_response.data:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid device_type."
                )
            supported_biomarkers = device_type_response.data["supported_biomarkers"]
            total_readings = 0
            biomarkers_generated = set()
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=days_of_history)
            for day_offset in range(days_of_history):
                current_date = start_date + timedelta(days=day_offset)
                for biomarker in supported_biomarkers:
                    # Generate random number of readings per biomarker type
                    if biomarker == "heart_rate":
                        num_readings = random.randint(3, 5)
                    elif biomarker in ["blood_pressure_systolic", "blood_pressure_diastolic"]:
                        num_readings = random.randint(2, 3)
                    elif biomarker == "glucose":
                        num_readings = random.randint(8, 12)
                    elif biomarker == "steps":
                        num_readings = 1
                    elif biomarker == "sleep":
                        num_readings = 1
                    else:
                        num_readings = 1
                    
                    for _ in range(num_readings):
                        value = await BiomarkerService.generate_random_biomarker_value(biomarker)
                        recorded_at = current_date + timedelta(
                            hours=random.randint(0, 23),
                            minutes=random.randint(0, 59),
                            seconds=random.randint(0, 59)
                        )
                        insert_data = {
                            "user_id": user_id,
                            "device_id": device_id,
                            "biomarker_type": biomarker,
                            "value": value,
                            "unit": BiomarkerService.get_unit_for_biomarker(biomarker),
                            "source": "device",
                            "recorded_at": recorded_at,
                            "notes": None
                        }
                        supabase_admin.table("biomarkers").insert(insert_data).execute()
                        total_readings += 1
                        biomarkers_generated.add(biomarker)
            return {
                "total_readings": total_readings,
                "biomarkers_generated": list(biomarkers_generated),
                "date_range": {"start": start_date.isoformat(), "end": end_date.isoformat()}
            }
        except HTTPException as he:
            raise he
        except Exception as e:
            logger.exception("Unexpected error simulating device data")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred."
            )

    @staticmethod
    async def generate_random_biomarker_value(biomarker_type: str) -> float:
        """
        Generate a random realistic value for a specific biomarker type

        Uses healthy ranges from biomarker_ranges table with slight random variation

        Args:
            biomarker_type: Type of biomarker

        Returns:
            Random value within healthy range

        TODO: Implement this function
        - Query biomarker_ranges for the type
        - Generate random value between min_optimal and max_optimal
        - Add slight variation (+/- 10%) for realism
        - Return the generated value
        """
        try:
            range_response = supabase_admin.table("biomarker_ranges")\
                .select("*")\
                .eq("biomarker_type", biomarker_type)\
                .single()\
                .execute()
            if not range_response.data:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid biomarker_type for value generation."
                )
            r = range_response.data
            base_value = random.uniform(r["optimal_min"], r["optimal_max"])
            variation = base_value * random.uniform(-0.1, 0.1)  # +/- 10%
            return round(base_value + variation, 2)
        except HTTPException as he:
            raise he    
        except Exception as e:
            logger.exception("Unexpected error generating random biomarker value")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred."
            )    


# Create singleton instance
biomarker_service = BiomarkerService()
