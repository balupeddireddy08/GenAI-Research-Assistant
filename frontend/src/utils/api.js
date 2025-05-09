/**
 * API utilities for the GenAI Research Assistant frontend
 * Handles all communication with the backend API
 */

const API_BASE_URL = 'http://localhost:8000/api';

/**
 * Send a chat message and get a response
 * 
 * @param {string} message - The user's message
 * @param {string|null} conversationId - Optional conversation ID for continuing a conversation
 * @param {Object|null} metadata - Optional metadata to include with the message
 * @returns {Promise<Object>} - The response data including message and conversation info
 */
export const sendChatMessage = async (message, conversationId = null, metadata = null) => {
  try {
    const response = await fetch(`${API_BASE_URL}/chat/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        message,
        conversation_id: conversationId,
        metadata
      }),
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || 'Failed to send message');
    }

    return await response.json();
  } catch (error) {
    console.error('Error sending chat message:', error);
    throw error;
  }
};

/**
 * Get conversation history
 * 
 * @param {number} skip - Number of items to skip (for pagination)
 * @param {number} limit - Maximum number of conversations to return
 * @returns {Promise<Array>} - List of conversation objects
 */
export const getConversationHistory = async (skip = 0, limit = 20) => {
  try {
    const response = await fetch(`${API_BASE_URL}/history/?skip=${skip}&limit=${limit}`);
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || 'Failed to fetch conversation history');
    }

    return await response.json();
  } catch (error) {
    console.error('Error fetching conversation history:', error);
    throw error;
  }
};

/**
 * Get a specific conversation with all its messages
 * 
 * @param {string} conversationId - The ID of the conversation to fetch
 * @returns {Promise<Object>} - The conversation data including messages
 */
export const getConversation = async (conversationId) => {
  try {
    const response = await fetch(`${API_BASE_URL}/history/${conversationId}`);
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || 'Failed to fetch conversation');
    }

    return await response.json();
  } catch (error) {
    console.error('Error fetching conversation:', error);
    throw error;
  }
};

/**
 * Delete a conversation
 * 
 * @param {string} conversationId - The ID of the conversation to delete
 * @returns {Promise<void>}
 */
export const deleteConversation = async (conversationId) => {
  try {
    const response = await fetch(`${API_BASE_URL}/history/${conversationId}`, {
      method: 'DELETE',
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || 'Failed to delete conversation');
    }

    return true;
  } catch (error) {
    console.error('Error deleting conversation:', error);
    throw error;
  }
};

/**
 * Get recommendations for a conversation
 * 
 * @param {string} conversationId - The ID of the conversation
 * @returns {Promise<Array>} - List of recommendation objects
 */
export const getRecommendations = async (conversationId) => {
  try {
    const response = await fetch(`${API_BASE_URL}/recommendations/${conversationId}`);
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || 'Failed to fetch recommendations');
    }

    return await response.json();
  } catch (error) {
    console.error('Error fetching recommendations:', error);
    throw error;
  }
}; 