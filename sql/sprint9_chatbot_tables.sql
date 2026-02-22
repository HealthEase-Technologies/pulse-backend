-- Sprint 9.1 - AI Chatbot Tables
-- Chat message storage for conversation history

-- Chat messages table
CREATE TABLE IF NOT EXISTS chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_chat_messages_user_id ON chat_messages(user_id);
CREATE INDEX IF NOT EXISTS idx_chat_messages_created_at ON chat_messages(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_chat_messages_user_created ON chat_messages(user_id, created_at DESC);

-- RLS Policies
ALTER TABLE chat_messages ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only view their own chat messages
CREATE POLICY chat_messages_select_own ON chat_messages
    FOR SELECT
    USING (auth.uid() = user_id);

-- Policy: Users can only insert their own chat messages
CREATE POLICY chat_messages_insert_own ON chat_messages
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Policy: Users can only delete their own chat messages
CREATE POLICY chat_messages_delete_own ON chat_messages
    FOR DELETE
    USING (auth.uid() = user_id);

-- Comments
COMMENT ON TABLE chat_messages IS 'Stores chat conversation history between users and AI chatbot';
COMMENT ON COLUMN chat_messages.role IS 'Message sender: user, assistant (AI), or system';
COMMENT ON COLUMN chat_messages.content IS 'The message content/text';
