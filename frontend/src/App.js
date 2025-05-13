import React, { useState, useEffect, useRef } from 'react';
import { Mic, Send, Lightbulb, History, X, Copy, StopCircle, RefreshCw } from 'lucide-react';
import { sendChatMessage, getConversationHistory, getConversation, fixConversationTimestamps } from './utils/api';

function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isGeneratingPrompt, setIsGeneratingPrompt] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [quickActions, setQuickActions] = useState({
    tags: ['AI', 'NLP', 'Robotics'],
    domains: [
      'Medicine', 'Engineering', 'Education', 'Agriculture'
    ],
    recommendationTags: []
  });
  const [recommendations, setRecommendations] = useState([]);
  const [chatHistory, setChatHistory] = useState([]);
  const [showHistory, setShowHistory] = useState(true);
  const [showQuickActions, setShowQuickActions] = useState(true);
  const [currentConversationId, setCurrentConversationId] = useState(null);
  const [errorMessage, setErrorMessage] = useState(null);
  const [processingStatus, setProcessingStatus] = useState(null);
  const [detailsModal, setDetailsModal] = useState({ show: false, data: null });
  const [historyFilter, setHistoryFilter] = useState('');
  const [activeRecommendationTag, setActiveRecommendationTag] = useState(null);

  // Track if this is a new session
  const [isNewSession, setIsNewSession] = useState(true);

  // Add a state to track if a message is being regenerated
  const [regeneratingMessage, setRegeneratingMessage] = useState(false);
  
  // Add a state to track the cancellation status
  const [isCancelled, setIsCancelled] = useState(false);

  // At the beginning of the component, add a new state for history loading
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);

  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);

  // CSS for custom classes
  const customStyles = `
    .fit-content {
      width: fit-content !important;
      max-width: 100%;
    }
  `;

  // Auto-scroll to the latest message
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth', block: 'end' });
    }
  }, [messages.length]);

  // Auto-resize textarea and set focus
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = textareaRef.current.scrollHeight + 'px';
    }
  }, [input]);

  // Initial load of conversation history
  useEffect(() => {
    // Load conversation history on component mount
    const loadHistory = async () => {
      setIsLoadingHistory(true);
      
      try {
        // Using a direct call to the API here to have more control over processing
        const history = await getConversationHistory();
        
        // Current date for comparison
        const now = new Date();
        
        // Process titles for better display on first load
        const processedHistory = history.map(conv => {
          // If title is poor quality (too short or generic), mark it for better display
          if (conv.title && (
              conv.title.length < 5 || 
              /^(hi|hello|hey|test)$/i.test(conv.title.trim())
          )) {
            // Just improve the title, don't change timestamps
            return {
              ...conv,
              displayTitle: "Unnamed Research Query"
            };
          }
          
          // Check if this is a today's conversation
          try {
            const convDate = conv.updated_at ? new Date(conv.updated_at) : 
                          (conv.created_at ? new Date(conv.created_at) : null);
            
            // Skip invalid dates or future dates
            if (!convDate || isNaN(convDate.getTime()) || convDate > now) {
              return conv;
            }
            
            if (convDate && now.toDateString() === convDate.toDateString()) {
              // Mark today's conversations for special styling
              return {
                ...conv,
                isToday: true
              };
            }
          } catch (err) {
            console.error("Error checking date for today's conversation:", err);
          }
          
          return conv;
        });
        
        console.log("Loaded and processed conversation history:", processedHistory);
        
        // Sort the history properly
        const sortedHistory = sortConversations(processedHistory);
        
        setChatHistory(sortedHistory || []);
      } catch (error) {
        console.error("Error loading conversation history:", error);
        setErrorMessage("Failed to load conversation history. Using local storage only.");
        // Use empty array if history can't be loaded
        setChatHistory([]);
      }
      setIsLoadingHistory(false);
    };

    loadHistory();
  }, []);

  // New helper function to consistently sort conversations
  const sortConversations = (conversations) => {
    // Get current date for comparison
    const now = new Date();
    
    return [...conversations].sort((a, b) => {
      // Current active conversation always comes first
      if (a.id === currentConversationId && b.id !== currentConversationId) return -1;
      if (a.id !== currentConversationId && b.id === currentConversationId) return 1;
      
      // Temporary (in-progress) conversations come next
      if (a.isTemp && !b.isTemp) return -1;
      if (!a.isTemp && b.isTemp) return 1;
      
      // Today's conversations come next
      const aIsToday = a.isToday || false;
      const bIsToday = b.isToday || false;
      
      if (aIsToday && !bIsToday) return -1;
      if (!aIsToday && bIsToday) return 1;
      
      // Then sort by date, ensuring we don't prioritize future dates
      try {
        // Parse dates safely
        let dateA = a.updated_at ? new Date(a.updated_at) : 
                   (a.created_at ? new Date(a.created_at) : new Date(0));
        let dateB = b.updated_at ? new Date(b.updated_at) : 
                   (b.created_at ? new Date(b.created_at) : new Date(0));
        
        // Check for invalid dates and future dates
        if (isNaN(dateA.getTime()) || dateA > now) {
          // If the date is invalid or in the future, treat it as very old
          dateA = new Date(0);
        }
        if (isNaN(dateB.getTime()) || dateB > now) {
          // If the date is invalid or in the future, treat it as very old
          dateB = new Date(0);
        }
        
        // Sort newest first (always descending order)
        return dateB - dateA;
      } catch (err) {
        console.error("Error comparing dates:", err);
        return 0;
      }
    });
  };

  // Initial welcome message effect
  useEffect(() => {
    // Set the welcome message immediately when component mounts
    setMessages([{
      role: 'assistant',
      content: 'Welcome to the GenAI Research Assistant! How can I help with your research today?',
      id: Date.now()
    }]);
  }, []);

  const handleQuickAction = (action) => {
    // Add the action text to input and focus the textarea
    setInput(prev => (prev.trim() ? prev + ' ' : '') + action);
    
    // Add a small delay to ensure the state update has completed
    setTimeout(() => {
      if (textareaRef.current) {
        textareaRef.current.focus();
        // Manually trigger resize of textarea
        textareaRef.current.style.height = 'auto';
        textareaRef.current.style.height = textareaRef.current.scrollHeight + 'px';
      }
    }, 10);
  };

  // Add a function to handle regenerating a response
  const handleRegenerateResponse = async () => {
    if (regeneratingMessage || isLoading) return;
    
    // Get the last user message 
    const lastUserMessage = [...messages].reverse().find(m => m.role === 'user');
    
    if (!lastUserMessage) return;
    
    // Set states for regeneration
    setRegeneratingMessage(true);
    setIsLoading(true);
    
    // Remove the last assistant message
    setMessages(prevMessages => prevMessages.filter(m => m.id !== messages[messages.length - 1].id));
    
    try {
      // Resubmit the last user message
      const response = await sendChatMessage(
        lastUserMessage.content, 
        currentConversationId
      );
      
      // Create bot response from API
      const botResponse = {
        role: 'assistant',
        content: response.message.content,
        id: response.message.id || Date.now() + 1,
        processingStatus: response.processing_status,
        metadata: response.message.metadata,
        sources: response.sources || [] 
      };

      setMessages(prevMessages => [...prevMessages, botResponse]);
      
      // Update recommendations if available
      if (botResponse.metadata && botResponse.metadata.recommendations) {
        setRecommendations(botResponse.metadata.recommendations);
      }
      
    } catch (error) {
      console.error("Error regenerating response:", error);
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: 'Error regenerating response: ' + (error.message || 'Unknown error'),
        isError: true, 
        id: Date.now() 
      }]);
      
      setErrorMessage(error.message || 'Failed to regenerate response.');
    } finally {
      setRegeneratingMessage(false);
      setIsLoading(false);
    }
  };
  
  // Add a function to cancel processing
  const cancelProcessing = () => {
    if (!isLoading) return;
    
    setIsCancelled(true);
    setIsLoading(false);
    setProcessingStatus(null);
    
    // Add a cancellation message
    setMessages(prev => [...prev, { 
      role: 'assistant', 
      content: 'Processing was cancelled.',
      isSystem: true,
      id: Date.now() 
    }]);
    
    // Reset the cancellation state after a delay
    setTimeout(() => setIsCancelled(false), 500);
  };

  // Update the refreshHistory function to use the new sorting helper
  const refreshHistory = async (fixTimestamps = false) => {
    try {
      setIsLoadingHistory(true);
      console.log("Refreshing conversation history...");
      
      // Fix timestamps if requested (or if there was a previous issue)
      if (fixTimestamps) {
        try {
          const result = await fixConversationTimestamps();
          console.log("Fixed timestamps result:", result);
          // Show a brief success message
          setErrorMessage(`Success: ${result.message}`);
          // Clear the success message after 3 seconds
          setTimeout(() => {
            if (errorMessage && errorMessage.startsWith('Success:')) {
              setErrorMessage(null);
            }
          }, 3000);
        } catch (error) {
          console.error("Error fixing timestamps:", error);
          // Don't show error to avoid disrupting main flow
        }
      }
      
      // Save existing displayTitles and temporary conversations to reapply them after refresh
      const existingDisplayTitles = {};
      const tempConversations = [];
      chatHistory.forEach(conv => {
        if (conv.displayTitle) {
          existingDisplayTitles[conv.id] = conv.displayTitle;
        }
        // Save temporary conversations to add back to history after refresh
        if (conv.isTemp) {
          tempConversations.push(conv);
        }
      });
      
      // Force cache-busting by adding timestamp to the URL
      const history = await getConversationHistory();
      console.log("Updated conversation history:", history);
      
      // Current date for comparison
      const now = new Date();
      
      // Process each conversation entry
      let updatedHistory = history.map(conv => {
        // 1. First try to preserve existing custom display titles
        if (existingDisplayTitles[conv.id]) {
          return { ...conv, displayTitle: existingDisplayTitles[conv.id] };
        }
        
        // 2. For items without displayTitle but with poor title quality, generate a better one
        if (conv.title && (
            conv.title.length < 5 || 
            /^(hi|hello|hey|test)$/i.test(conv.title.trim())
        )) {
          // Don't use "Conversation" prefix or dates in the title
          return { ...conv, displayTitle: "Unnamed Research Query" };
        }
        
        // 3. Check if this is a new conversation from today that needs special handling
        try {
          const convDate = conv.updated_at ? new Date(conv.updated_at) : 
                           (conv.created_at ? new Date(conv.created_at) : null);
          
          // Skip invalid dates or future dates
          if (!convDate || isNaN(convDate.getTime()) || convDate > now) {
            return conv;
          }
          
          if (convDate && now.toDateString() === convDate.toDateString()) {
            // This is today's conversation - ensure it has the proper display updates
            console.log("Found today's conversation:", conv.id);
            return { ...conv, isToday: true };
          }
        } catch (err) {
          console.error("Error processing date in conversation:", err);
        }
        
        return conv;
      });
      
      // Add back temporary conversations that don't exist in the API yet
      // This ensures user's current conversation stays in the history while waiting for API
      if (tempConversations.length > 0) {
        console.log("Adding temporary conversations back to history:", tempConversations);
        
        // Only add temp conversations that don't have a real version in the API results
        const apiConversationIds = new Set(history.map(c => c.id));
        const tempToAdd = tempConversations.filter(temp => {
          // Keep temp conversations without a real ID,
          // or if the current conversation ID is still using the temp ID
          return !apiConversationIds.has(temp.id) || currentConversationId === temp.id;
        });
        
        // Combine API history with temp conversations
        updatedHistory = [...tempToAdd, ...updatedHistory];
      }
      
      // Sort the combined history using our helper function
      updatedHistory = sortConversations(updatedHistory);
      
      setChatHistory(updatedHistory || []);
      setIsLoadingHistory(false);
      return updatedHistory;
    } catch (error) {
      console.error("Error refreshing conversation history:", error);
      setIsLoadingHistory(false);
      return null;
    }
  };

  // Add a helper function to extract meaningful titles from user messages
  const extractMeaningfulTitle = (message) => {
    if (!message) return "Unnamed Research Query";
    
    // Trim whitespace and replace multiple spaces with a single space
    let processedMessage = message.trim().replace(/\s+/g, ' ');
    
    // Check if the message is empty after processing
    if (!processedMessage) return "Unnamed Research Query";
    
    // If message is a simple greeting, return a generic title
    if (/^(hi|hello|hey|test|hi there|hello there)$/i.test(processedMessage)) {
      return "Unnamed Research Query";
    }
    
    // Try to extract a meaningful part if it's a question or command
    if (processedMessage.includes('?')) {
      const question = processedMessage.split('?')[0] + '?';
      if (question.length > 10) {
        return question.slice(0, 50) + (question.length > 50 ? '...' : '');
      }
    }
    
    // For "Compare X and Y" or similar research requests
    if (/^(compare|analyze|research|explain|summarize|tell me about|what is)/i.test(processedMessage)) {
      return processedMessage.slice(0, 50) + (processedMessage.length > 50 ? '...' : '');
    }
    
    // Default: truncate to reasonable length for a title
    return processedMessage.slice(0, 50) + (processedMessage.length > 50 ? '...' : '');
  };

  // Modified sendMessage function to check for cancellation
  const sendMessage = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage = { role: 'user', content: input.trim() };
    const messageId = Date.now();
    setErrorMessage(null);
    setProcessingStatus(null);
    setIsCancelled(false);

    // Add user message to chat
    setMessages(prev => [...prev, { ...userMessage, id: messageId }]);
    setInput('');
    setIsLoading(true);

    // For new conversations, add to history immediately after user sends first message
    // This ensures the conversation appears in history before the AI responds
    if (isNewSession) {
      const tempConversationId = `temp-${Date.now()}`;
      const title = extractMeaningfulTitle(userMessage.content);
      
      // Create a temporary conversation entry for the history sidebar
      const newConversation = {
        id: tempConversationId,
        title: title,
        displayTitle: title,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        message_count: 1,
        isToday: true,
        isTemp: true // Mark as temporary until we get real ID from API
      };
      
      // Add to history at the top
      setChatHistory(prev => [newConversation, ...prev]);
      
      // Set the temporary conversation as current (will be updated when API responds)
      setCurrentConversationId(tempConversationId);
    }

    try {
      // Log that we're continuing or starting a conversation
      console.log(`${currentConversationId ? 'Continuing conversation' : 'Starting new conversation'}: ${currentConversationId || 'new'}`);
      
      // If this is continuing an existing conversation, also log the number of existing messages
      if (currentConversationId) {
        console.log(`Conversation has ${messages.length} messages in context`);
      }
      
      // Check for cancellation
      if (isCancelled) {
        setIsLoading(false);
        return;
      }

      // Send message to backend API
      const response = await sendChatMessage(
        userMessage.content, 
        currentConversationId && !currentConversationId.startsWith('temp-') ? currentConversationId : null
      );
      
      // Check for cancellation again
      if (isCancelled) {
        setIsLoading(false);
        return;
      }

      console.log("Response received:", response);
      console.log("Processing status:", response.processing_status);
      console.log("Sources in response:", response.sources);
      
      // Update the processing status state
      setProcessingStatus(response.processing_status);

      // Update conversation ID if this is a new conversation
      if (response.conversation_id) {
        console.log(`Setting conversation ID to: ${response.conversation_id}`);
        
        // If we had a temporary ID, replace it in the history
        if (isNewSession || currentConversationId?.startsWith('temp-')) {
          // Update the temporary conversation with the real ID
          setChatHistory(prev => prev.map(conv => 
            (conv.isTemp && (conv.id === currentConversationId || currentConversationId?.startsWith('temp-'))) ? {
              ...conv,
              id: response.conversation_id,
              isTemp: false
            } : conv
          ));
        }
        
        // Set the current conversation ID to the real one from API
        setCurrentConversationId(response.conversation_id);
        setIsNewSession(false);
      }

      // Create bot response from API
      const botResponse = {
        role: 'assistant',
        content: response.message.content,
        id: response.message.id || Date.now() + 1,
        processingStatus: response.processing_status,
        metadata: response.message.metadata,
        sources: response.sources || [] // Add sources from the API response
      };

      setMessages(prevMessages => [...prevMessages, botResponse]);

      // Update recommendations from the response metadata
      if (botResponse.metadata && botResponse.metadata.recommendations) {
        // Extract recommendations and sort by relevance score (already sorted from backend)
        const newRecommendations = botResponse.metadata.recommendations;
        setRecommendations(newRecommendations);
        
        // Update recommendation tags if available
        if (botResponse.metadata.recommendation_tags && botResponse.metadata.recommendation_tags.length > 0) {
          setQuickActions(prev => ({
            ...prev,
            recommendationTags: botResponse.metadata.recommendation_tags
          }));
        }
        
        console.log(`Added ${newRecommendations.length} recommendations from response metadata`);
      }

      // Update the message count in history
      setChatHistory(prev => prev.map(conv => 
        conv.id === response.conversation_id ? {
          ...conv,
          message_count: (conv.message_count || 0) + 1
        } : conv
      ));

      // Refresh conversation history
      await refreshHistory();

      setIsLoading(false);
    } catch (error) {
      // Don't show error if we cancelled
      if (isCancelled) {
        setIsLoading(false);
        return;
      }
    
      console.error("Error sending message:", error);
      setIsLoading(false);
      setProcessingStatus(null);
      
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: 'Error processing your request: ' + (error.message || 'Unknown error'),
        isError: true, 
        id: Date.now() 
      }]);
      
      setErrorMessage(error.message || 'Failed to send message.');
    }
  };

  // Function to update processing status during API call
  useEffect(() => {
    if (isLoading && processingStatus) {
      // This could be expanded to poll for status updates from the server
      const statusInterval = setInterval(() => {
        // In a real implementation, you might fetch the latest status
        console.log("Current processing status:", processingStatus);
      }, 1000);
      
      return () => clearInterval(statusInterval);
    }
  }, [isLoading, processingStatus]);

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const generatePrompt = async () => {
    if (isGeneratingPrompt || !input.trim()) return;
    
    const userInput = input.trim();
    setIsGeneratingPrompt(true);
    setProcessingStatus({ message: "Enhancing your research query..." });
    
    try {
      // Save original input for fallback
      const originalInput = userInput;
      
      // Call the backend API to enhance the prompt
      const response = await fetch(`${process.env.REACT_APP_API_URL || 'http://localhost:8000/api'}/chat/enhance-prompt`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          prompt: userInput,
          conversation_id: currentConversationId // Include the current conversation ID if available
        }),
      });
      
      if (!response.ok) {
        throw new Error('Failed to enhance prompt');
      }
      
      const data = await response.json();
      
      // Update the input with the enhanced prompt
      setInput(data.enhanced_prompt);
      
      // Show a subtle notification that the prompt was enhanced
      setProcessingStatus({ message: "Query enhanced! Send to get more precise results." });
      
      // Reset after 3 seconds
      setTimeout(() => setProcessingStatus(null), 3000);
    } catch (error) {
      console.error("Error enhancing prompt:", error);
      setProcessingStatus({ message: "Could not enhance query. You can still send your original query." });
      
      // Reset status after 3 seconds
      setTimeout(() => setProcessingStatus(null), 3000);
    } finally {
      setIsGeneratingPrompt(false);
      if (textareaRef.current) {
        textareaRef.current.focus();
      }
    }
  };

  const startRecording = () => {
    if (isRecording) return;
    setIsRecording(true);
    console.log("Recording started (simulated).");
    setTimeout(() => {
       stopRecording();
    }, 3000);
  };

  const stopRecording = () => {
    if (!isRecording) return;
    setIsRecording(false);
    console.log("Recording stopped (simulated).");
    setInput(prev => prev + " [Simulated speech input text]");
    if (textareaRef.current) {
      textareaRef.current.focus();
    }
  };

  // Update the loadConversation function to use the helper
  const loadConversation = async (conversation) => {
    try {
      // Skip loading for temporary conversations that don't have an API ID yet
      if (conversation.isTemp) {
        console.log("Can't load temporary conversation that's still in progress");
        return;
      }
      
      setIsLoading(true);
      setErrorMessage(null);
      setProcessingStatus(null);

      // Get full conversation with messages from the API
      const fullConversation = await getConversation(conversation.id);
      
      console.log("Loaded conversation:", fullConversation);
      
      // Set current conversation ID
      setCurrentConversationId(fullConversation.id);
      
      // Mark this as a continued session, not a new one
      setIsNewSession(false);
      
      // Update messages
      setMessages(fullConversation.messages.map(msg => ({
        role: msg.role,
        content: msg.content,
        id: msg.id,
        processingStatus: msg.metadata?.processing_status || null,
        metadata: msg.metadata,
        sources: msg.metadata?.sources || [] // Add sources from metadata
      })));

      // Always extract a better title from the first user message
      const firstUserMessage = fullConversation.messages.find(m => m.role === 'user');
      if (firstUserMessage && firstUserMessage.content) {
        const betterTitle = extractMeaningfulTitle(firstUserMessage.content);
        // Only update display title if it's better than the existing one
        if (betterTitle !== "Unnamed Research Query" || 
            !fullConversation.title || 
            fullConversation.title.length < 5 || 
            /^(hi|hello|hey|test)$/i.test(fullConversation.title.trim())) {
          // Update conversation in local state only (for UI display)
          setChatHistory(prev => prev.map(c => 
            c.id === fullConversation.id ? {...c, displayTitle: betterTitle} : c
          ));
        }
      }

      console.log(`Loaded ${fullConversation.messages.length} messages from conversation history`);

      // Force refresh history immediately to get updated timestamps
      await refreshHistory();

      // Auto-scroll to the last message after a short delay
      setTimeout(() => {
        if (messagesEndRef.current) {
          messagesEndRef.current.scrollIntoView({ behavior: 'smooth', block: 'end' });
        }
      }, 100);

      setIsLoading(false);
    } catch (error) {
      console.error("Error loading conversation:", error);
      setIsLoading(false);
      setErrorMessage("Failed to load conversation.");
    }
  };

  const showProcessingDetails = (status) => {
    setDetailsModal({
      show: true,
      data: status
    });
  };

  const hideModal = () => {
    setDetailsModal({ show: false, data: null });
  };

  // Render loading indicator with processing status
  const renderLoadingIndicator = () => {
    if (!isLoading) return null;
    
    return (
      <div className="p-4 rounded-xl bg-white max-w-md mr-auto rounded-bl-lg rounded-tr-lg shadow border border-gray-200">
        <div className="space-y-3">
          <div className="flex space-x-1 items-center">
            <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce"></div>
            <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce delay-150"></div>
            <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce delay-300"></div>
            <span className="ml-2 text-sm text-gray-500">Processing your request...</span>
          </div>
          
          {processingStatus && (
            <div className="space-y-2">
              <div className="w-full bg-gray-200 rounded-full h-1.5">
                <div 
                  className="bg-blue-600 h-1.5 rounded-full" 
                  style={{ width: `${processingStatus.progress_percent || 0}%` }}
                ></div>
              </div>
              
              <div className="text-xs text-gray-500">
                <p className="font-medium">
                  {processingStatus.current_step && processingStatus.detailed_status && 
                    (processingStatus.detailed_status[processingStatus.current_step]?.message || 
                    `Processing: ${processingStatus.current_step || "starting"}`)}
                </p>
                <p className="text-gray-400 mt-1">
                  Step {processingStatus.steps_completed?.length || 0} of {processingStatus.steps_total || 4}
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    );
  };

  // Add this effect for handling ESC key press
  useEffect(() => {
    const handleEscKey = (e) => {
      if (e.key === 'Escape' && detailsModal.show) {
        hideModal();
      }
    };
    
    window.addEventListener('keydown', handleEscKey);
    return () => {
      window.removeEventListener('keydown', handleEscKey);
    };
  }, [detailsModal.show]);

  // Reset modal when changing conversations
  useEffect(() => {
    setDetailsModal({ show: false, data: null });
  }, [currentConversationId]);

  // Update the renderConversationItem function to display proper titles and dates
  const renderConversationItem = (conv) => {
    // Check if this is the current conversation (handles both temp and real IDs)
    const isActive = conv.id === currentConversationId || 
                    (conv.isTemp && currentConversationId?.startsWith('temp-'));
    
    // Get the conversation timestamp (prefer updated_at over created_at)
    let timestamp = null;
    if (conv.updated_at) {
      try {
        timestamp = new Date(conv.updated_at);
        // Validate timestamp - if invalid or future date, try created_at
        if (isNaN(timestamp.getTime()) || timestamp > new Date()) {
          timestamp = null;
        }
      } catch (e) {
        timestamp = null;
      }
    }
    
    // If updated_at wasn't valid, try created_at
    if (!timestamp && conv.created_at) {
      try {
        timestamp = new Date(conv.created_at);
        // Validate timestamp - if invalid or future date, use current date
        if (isNaN(timestamp.getTime()) || timestamp > new Date()) {
          timestamp = null;
        }
      } catch (e) {
        timestamp = null;
      }
    }
    
    // If no valid timestamp was found, use current date only for display
    if (!timestamp) {
      timestamp = new Date();
    }
    
    // Check if this is today's conversation
    const now = new Date();
    const isToday = timestamp.toDateString() === now.toDateString();
    
    // Format different date displays
    let formattedDate;
    
    if (isToday) {
      // For today's conversations, show "Today, HH:MM AM/PM"
      formattedDate = 'Today, ' + timestamp.toLocaleTimeString([], { 
        hour: '2-digit', 
        minute: '2-digit' 
      });
    } else {
      // Check if it's yesterday
      const yesterday = new Date();
      yesterday.setDate(yesterday.getDate() - 1);
      const isYesterday = timestamp.toDateString() === yesterday.toDateString();
      
      if (isYesterday) {
        // For yesterday's conversations, show "Yesterday, HH:MM AM/PM"
        formattedDate = 'Yesterday, ' + timestamp.toLocaleTimeString([], { 
          hour: '2-digit', 
          minute: '2-digit' 
        });
      } else if (timestamp.getFullYear() === now.getFullYear()) {
        // For same year but not today/yesterday, show "Mon DD, HH:MM AM/PM"
        formattedDate = timestamp.toLocaleDateString([], {
          month: 'short',
          day: 'numeric'
        }) + ', ' + timestamp.toLocaleTimeString([], { 
          hour: '2-digit', 
          minute: '2-digit' 
        });
      } else {
        // For previous years, show "Mon DD YYYY, HH:MM AM/PM"
        formattedDate = timestamp.toLocaleDateString([], {
          year: 'numeric',
          month: 'short',
          day: 'numeric'
        }) + ', ' + timestamp.toLocaleTimeString([], { 
          hour: '2-digit', 
          minute: '2-digit' 
        });
      }
    }
    
    // Use displayTitle if available, otherwise use the original title
    // If both are missing or low quality, use a placeholder
    let displayTitle = conv.displayTitle || conv.title || "Unnamed Research Query";
    
    // If this is a temporary conversation in progress, show a special indicator
    const isTempInProgress = conv.isTemp && isActive;
    
    return (
      <button
        key={conv.id}
        onClick={() => loadConversation(conv)}
        className={`w-full text-left p-3 rounded-md shadow-sm hover:bg-blue-50 cursor-pointer transition duration-150 border ${
          isActive 
            ? 'border-blue-400 bg-blue-50 shadow-md' 
            : isToday ? 'border-blue-200 bg-blue-50/30' : 'border-gray-100 bg-white'
        } focus:outline-none focus:ring-2 focus:ring-blue-300`}
      >
        <p className="font-medium text-gray-800 text-sm truncate flex items-center">
          {isActive && (
            <span className={`w-2 h-2 rounded-full mr-2 flex-shrink-0 ${
              isTempInProgress ? 'bg-yellow-500 animate-pulse' : 'bg-blue-500'
            }`} aria-hidden="true"></span>
          )}
          {isToday && !isActive && (
            <span className="w-2 h-2 bg-blue-300 rounded-full mr-2 flex-shrink-0" aria-hidden="true"></span>
          )}
          <span className="truncate" title={displayTitle}>
            {isTempInProgress ? `${displayTitle} (typing...)` : displayTitle}
          </span>
        </p>
        <div className="flex justify-between items-center mt-1">
          <p className="text-xs text-gray-500 font-medium">
            {formattedDate}
          </p>
          {conv.message_count && (
            <span className="text-xs bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded-full">
              {conv.message_count}
            </span>
          )}
        </div>
      </button>
    );
  };

  const getSources = (message) => {
    const sources = [];
    
    // NEW: Check if the message itself has a sources property (direct sources)
    if (message.sources && Array.isArray(message.sources)) {
      sources.push(...message.sources);
    }
    
    // Check in metadata.sources
    if (message.metadata && Array.isArray(message.metadata.sources)) {
      sources.push(...message.metadata.sources);
    }
    
    // Check in metadata.references
    if (message.metadata && Array.isArray(message.metadata.references)) {
      sources.push(...message.metadata.references);
    }
    
    // Check in processingStatus for academic_agent sources
    if (message.processingStatus && message.processingStatus.detailed_status) {
      // Check academic_agent sources
      const academicAgent = message.processingStatus.detailed_status.academic_agent;
      if (academicAgent) {
        if (Array.isArray(academicAgent.sources)) {
          sources.push(...academicAgent.sources);
        }
        // Also check for sources within the results (for arXiv papers)
        if (Array.isArray(academicAgent.results)) {
          academicAgent.results.forEach(result => {
            sources.push({
              url: result.url,
              title: result.title,
              description: result.abstract,
              type: "academic",
              arxiv_id: result.id,
              authors: result.authors
            });
          });
        }
      }
      
      // Check search_agent results
      const searchAgent = message.processingStatus.detailed_status.search_agent;
      if (searchAgent && Array.isArray(searchAgent.results)) {
        sources.push(...searchAgent.results.map(result => ({
          url: result.url || result.link,
          title: result.title,
          description: result.snippet || result.description,
          type: "web"
        })));
      }
      
      // Look for sources in any agent result
      Object.values(message.processingStatus.detailed_status)
        .filter(value => typeof value === 'object' && value !== null)
        .forEach(value => {
          if (Array.isArray(value.sources)) {
            sources.push(...value.sources);
          }
          if (Array.isArray(value.results)) {
            sources.push(...value.results.map(result => ({
              url: result.url || result.link,
              title: result.title || "Unknown Source",
              description: result.snippet || result.description || result.abstract,
              type: value.source === "arxiv" ? "academic" : "web",
              arxiv_id: result.id
            })));
          }
        });
    }
    
    // Filter out duplicates based on URL
    const uniqueSources = [];
    const seenUrls = new Set();
    
    sources.forEach(source => {
      if (source && source.url && !seenUrls.has(source.url)) {
        seenUrls.add(source.url);
        uniqueSources.push({
          url: source.url,
          title: source.title || source.url,
          description: source.description || source.snippet || source.abstract || null,
          type: source.type || "web",
          arxiv_id: source.arxiv_id,
          authors: source.authors
        });
      }
    });
    
    return uniqueSources;
  };

  // Improve the rendering function for better formatting
  const renderFormattedMessage = (content) => {
    // Don't process empty content
    if (!content) return null;

    try {
      // Replace markdown headings with properly styled elements
      let processedContent = content
        // Process main headings (# Heading)
        .replace(/^# (.+)$/gm, '<h1 class="text-2xl font-bold text-gray-800 mb-3 mt-2 pb-1 border-b border-gray-200">$1</h1>')
        
        // Process subheadings (## Subheading)
        .replace(/^## (.+)$/gm, '<h2 class="text-xl font-semibold text-gray-700 mb-2 mt-4">$1</h2>')
        
        // Process tertiary headings (### Subheading)
        .replace(/^### (.+)$/gm, '<h3 class="text-lg font-medium text-gray-700 mb-2 mt-3">$1</h3>')
        
        // Process bullet points (* Item or - Item)
        .replace(/^\s*[*-] (.+)$/gm, '<li class="ml-5 text-gray-700 mb-1 list-disc">$1</li>')
        
        // Process links ([text](url))
        .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" class="text-blue-600 hover:underline" target="_blank" rel="noopener noreferrer">$1</a>')
        
        // Process bold text (**text**)
        .replace(/\*\*([^*]+)\*\*/g, '<strong class="font-bold">$1</strong>')
        
        // Process italic text (*text*)
        .replace(/\*([^*]+)\*/g, '<em class="italic">$1</em>')
        
        // Handle code blocks with proper formatting
        .replace(/```(?:(\w+)\n)?([\s\S]+?)```/g, (match, lang, code) => {
          const language = lang ? ` language-${lang}` : '';
          return `<pre class="bg-gray-100 p-3 rounded-md my-3 text-sm overflow-x-auto"><code class="block${language}">${code.replace(/</g, '&lt;').replace(/>/g, '&gt;')}</code></pre>`;
        })
        
        // Handle inline code (`code`)
        .replace(/`([^`]+)`/g, '<code class="bg-gray-100 text-red-600 px-1 py-0.5 rounded text-sm">$1</code>');
      
      // Add markdown table formatting support
      processedContent = processTableMarkdown(processedContent);
      
      // Better paragraph handling - split by double newlines but preserve lists
      const paragraphs = [];
      let currentParagraph = '';
      const lines = processedContent.split('\n');
      
      for (let i = 0; i < lines.length; i++) {
        const line = lines[i];
        const nextLine = i < lines.length - 1 ? lines[i + 1] : '';
        
        // Add current line to paragraph
        currentParagraph += line;
        
        // Check if this is a paragraph break (empty line followed by non-empty line)
        if (line.trim() === '' && nextLine.trim() !== '') {
          if (currentParagraph.trim()) {
            paragraphs.push(currentParagraph.trim());
          }
          currentParagraph = '';
        } else if (i === lines.length - 1) {
          // Last line
          if (currentParagraph.trim()) {
            paragraphs.push(currentParagraph.trim());
          }
        } else {
          // Add a newline if not at end
          currentParagraph += '\n';
        }
      }
      
      // Process each paragraph separately
      const processedParagraphs = paragraphs.map(para => {
        // If paragraph contains list items
        if (para.includes('<li class="ml-5 text-gray-700 mb-1 list-disc">')) {
          return `<ul class="my-2 list-disc pl-5">${para}</ul>`;
        }
        // Skip wrapping already processed elements (headings, code blocks, tables, etc.)
        else if (para.startsWith('<h1') || para.startsWith('<h2') || para.startsWith('<h3') || 
                para.startsWith('<pre') || para.startsWith('<ul') || para.startsWith('<table')) {
          return para;
        }
        // Regular paragraph
        else {
          return `<p class="mb-3">${para}</p>`;
        }
      });
      
      // Join everything back
      const finalContent = processedParagraphs.join('');
      
      // Return the content with HTML enabled and full text display
      return (
        <div
          dangerouslySetInnerHTML={{ __html: finalContent }}
          className="message-content text-gray-800 leading-relaxed w-full overflow-x-auto"
          style={{ lineHeight: '1.6', maxWidth: '100%' }}
        />
      );
    } catch (error) {
      console.error("Error processing markdown:", error);
      // Fallback to plain text if something goes wrong
      return <p style={{ whiteSpace: 'pre-wrap' }}>{content}</p>;
    }
  };
  
  // Add a helper function to process markdown tables
  const processTableMarkdown = (content) => {
    // Split content by lines to process tables
    const lines = content.split('\n');
    let inTable = false;
    let tableContent = [];
    let processedLines = [];
    
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      const trimmedLine = line.trim();
      
      // Check if this is a table row (starts with |)
      if (trimmedLine.startsWith('|') && trimmedLine.endsWith('|')) {
        if (!inTable) {
          // This is the start of a new table
          inTable = true;
          tableContent = [];
        }
        tableContent.push(line);
      } else if (inTable) {
        // We were in a table but this line is not a table row
        // Process the collected table
        processedLines.push(convertTableToHtml(tableContent));
        inTable = false;
        tableContent = [];
        
        // Don't forget to add the current non-table line
        processedLines.push(line);
      } else {
        // Regular line, not in a table
        processedLines.push(line);
      }
    }
    
    // Check if we were still processing a table at the end
    if (inTable && tableContent.length > 0) {
      processedLines.push(convertTableToHtml(tableContent));
    }
    
    return processedLines.join('\n');
  };
  
  // Function to convert markdown table to HTML
  const convertTableToHtml = (tableLines) => {
    if (tableLines.length < 3) {
      // A valid table should have at least header, separator, and one data row
      return tableLines.join('\n');
    }
    
    // Process the table header
    const headerRow = tableLines[0];
    const headerCells = headerRow
      .trim()
      .split('|')
      .filter(cell => cell.trim() !== '') // Remove empty cells from start/end
      .map(cell => `<th class="border border-gray-300 px-4 py-2 bg-gray-100 font-medium">${cell.trim()}</th>`)
      .join('');
    
    // Skip the separator row (index 1)
    
    // Process the data rows
    const dataRows = tableLines.slice(2).map(row => {
      const cells = row
        .trim()
        .split('|')
        .filter(cell => cell.trim() !== '')
        .map(cell => `<td class="border border-gray-300 px-4 py-2">${cell.trim()}</td>`)
        .join('');
      
      return `<tr>${cells}</tr>`;
    }).join('');
    
    // Create the final table HTML
    return `<div class="overflow-x-auto my-4">
      <table class="min-w-full border-collapse border border-gray-300 rounded-lg">
        <thead>
          <tr>${headerCells}</tr>
        </thead>
        <tbody>
          ${dataRows}
        </tbody>
      </table>
    </div>`;
  };

  // Add this function to filter recommendations by tag
  const filterRecommendationsByTag = (tag) => {
    if (tag === null || tag === activeRecommendationTag) {
      // If clicking the active tag, clear the filter
      setActiveRecommendationTag(null);
    } else {
      setActiveRecommendationTag(tag);
    }
  };

  // Add this function to get filtered recommendations
  const getFilteredRecommendations = () => {
    if (!activeRecommendationTag) {
      return recommendations;
    }
    return recommendations.filter(rec => 
      rec.type && rec.type.toLowerCase() === activeRecommendationTag.toLowerCase()
    );
  };

  // Add this function to the App component
  const handleFixTimestamps = async () => {
    try {
      setIsLoadingHistory(true);
      
      // Call the API to fix timestamps
      const result = await fixConversationTimestamps();
      console.log("Fixed timestamps result:", result);
      
      // Show a notification (could be enhanced with a toast)
      setErrorMessage(`Success: ${result.message}`);
      
      // Refresh the history to show the new timestamps
      await refreshHistory();
      
      // Clear the success message after 3 seconds
      setTimeout(() => {
        if (errorMessage && errorMessage.startsWith('Success:')) {
          setErrorMessage(null);
        }
      }, 3000);
      
    } catch (error) {
      console.error("Error fixing timestamps:", error);
      setErrorMessage(`Failed to fix timestamps: ${error.message}`);
    } finally {
      setIsLoadingHistory(false);
    }
  };

  return (
    <div className="flex h-screen w-full bg-gradient-to-br from-blue-50 to-purple-50">
      <style>{customStyles}</style>
      {/* Processing details modal */}
      {detailsModal.show && detailsModal.data && (
        <div 
          className="fixed inset-0 bg-black bg-opacity-60 flex items-center justify-center z-50 p-4"
          onClick={hideModal}
          key={`modal-${detailsModal.data.current_step || 'details'}`}
        >
          <div 
            className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col"
            onClick={e => e.stopPropagation()}
          >
            <div className="p-4 bg-blue-100 border-b flex justify-between items-center sticky top-0 z-10">
              <h3 className="text-lg font-semibold text-blue-900">Processing Details</h3>
              <button 
                onClick={hideModal} 
                className="text-gray-700 hover:text-red-600 p-2 bg-white rounded-full hover:bg-red-100 transition-colors shadow-sm"
                aria-label="Close modal"
              >
                <X size={20} />
              </button>
            </div>
            
            <div 
              className="overflow-y-auto p-4 flex-1" 
              style={{
                maxHeight: 'calc(80vh - 130px)',
                overflowY: 'auto',
                scrollbarWidth: 'thin',
                scrollbarColor: '#4B5563 #E5E7EB'
              }}
            >
              {/* Main content grid */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {/* Left column: Steps and progress */}
                <div className="md:col-span-1 space-y-4">
                  {detailsModal.data.steps_total && (
                    <div className="mb-4 bg-white p-4 rounded-lg shadow-sm border border-gray-200">
                      <div className="text-sm font-medium text-gray-700 mb-2">
                        Overall Progress: {detailsModal.data.progress_percent || 0}%
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-3">
                        <div 
                          className="bg-blue-600 h-3 rounded-full transition-all duration-500"
                          style={{ width: `${detailsModal.data.progress_percent || 0}%` }}
                        ></div>
                      </div>
                      {detailsModal.data.start_time && (
                        <div className="mt-3 text-sm text-gray-600 font-medium flex justify-between">
                          <span>Started: {new Date(detailsModal.data.start_time * 1000).toLocaleTimeString()}</span>
                          <span>Total: {Math.round((detailsModal.data.detailed_status?.completed?.time_taken || 0) * 100) / 100}s</span>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Results summary */}
                  {detailsModal.data.detailed_status && 
                  (detailsModal.data.detailed_status.execution_completed && 
                  detailsModal.data.detailed_status.execution_completed.result_count) && (
                    <div className="p-3 bg-green-50 rounded-lg border border-green-200 shadow-sm">
                      <p className="text-green-800 font-medium flex items-center">
                        <span role="img" aria-label="Success" className="mr-2">✅</span>
                        Found {detailsModal.data.detailed_status.execution_completed.result_count} results
                      </p>
                    </div>
                  )}
                </div>

                {/* Right column: Detailed step information */}
                <div className="md:col-span-2 space-y-4">
                  <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
                    <h4 className="font-medium text-gray-800 mb-2">Process Details</h4>
                    
                    <div className="space-y-4">
                      {/* Show the processing steps in sequence */}
                      {[
                        'analyzing_intent',
                        'intent_analyzed', 
                        'executing',
                        'execution_completed',
                        'synthesizing',
                        'generating_recommendations',
                        'response_ready',
                        'completed'
                      ].map((step, index) => {
                        if (!detailsModal.data.detailed_status) return null;
                        
                        const isCompleted = detailsModal.data.steps_completed?.includes(step);
                        const isCurrent = detailsModal.data.current_step === step;
                        const detail = detailsModal.data.detailed_status[step];
                        
                        return (
                          <div 
                            key={step} 
                            className={`p-4 rounded-md ${
                              isCompleted ? 'bg-green-50 border border-green-100' : 
                              isCurrent ? 'bg-blue-50 border border-blue-100 animate-pulse' : 'bg-gray-50 border border-gray-100'
                            }`}
                          >
                            <div className="flex justify-between items-center mb-2">
                              <h4 className={`font-medium ${isCompleted ? 'text-green-700' : isCurrent ? 'text-blue-700' : 'text-gray-700'}`}>
                                {index + 1}. {step.replace(/_/g, ' ').replace(/^\w/, c => c.toUpperCase())}
                              </h4>
                              {isCompleted && 
                                <span className="text-green-600 bg-green-100 rounded-full h-6 w-6 flex items-center justify-center" role="img" aria-label="Completed">
                                  ✓
                                </span>
                              }
                            </div>
                            
                            {detail && detail.message && (
                              <p className="text-sm text-gray-600 mt-1">
                                {detail.message}
                              </p>
                            )}
                            
                            {/* Display operations like searches */}
                            {detail && detail.operations && (
                              <ul className="list-disc ml-6 mt-2 text-xs text-gray-500 space-y-1">
                                {detail.operations.map((op, i) => (
                                  <li key={i} className="pl-1">{op}</li>
                                ))}
                              </ul>
                            )}

                            {/* Display specific details for certain steps */}
                            {step === 'intent_analyzed' && detail?.intent && (
                              <div className="mt-2 p-2 bg-blue-50 rounded border border-blue-100 text-xs">
                                <div className="font-medium text-blue-700 mb-1">Intent Analysis:</div>
                                <div className="grid grid-cols-1 gap-1">
                                  {Object.entries(detail.intent).map(([key, value]) => (
                                    <div key={key} className="flex">
                                      <span className="font-medium text-gray-600 mr-2">{key}:</span>
                                      <span className="text-gray-800">
                                        {typeof value === 'string' ? value : 
                                         Array.isArray(value) ? value.join(', ') : 
                                         JSON.stringify(value)}
                                      </span>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}

                            {/* Show plan details */}
                            {step === 'plan_generated' && detail?.plan && (
                              <div className="mt-2 p-2 bg-indigo-50 rounded border border-indigo-100 text-xs">
                                <div className="font-medium text-indigo-700 mb-1">Execution Plan:</div>
                                <div className="space-y-2">
                                  {detail.plan.map((planStep, i) => (
                                    <div key={i} className="p-1 bg-white rounded border border-indigo-50">
                                      <div className="font-medium">Agent: {planStep.agent}</div>
                                      <div className="text-gray-600 mt-1">Task: {planStep.task}</div>
                                      <div className="text-gray-500 italic">Priority: {planStep.priority}</div>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}

                            {/* Show tools/agents used under Executing step */}
                            {step === 'executing' && (
                              <div className="mt-3 p-2 bg-green-50 rounded border border-green-100 text-xs">
                                <div className="font-medium text-green-700 mb-2">Tools Used:</div>
                                <div className="space-y-2">
                                  {Object.entries(detailsModal.data.detailed_status || {})
                                    .filter(([key]) => key.includes('agent_') || key.includes('academic_agent') || key.includes('search_agent'))
                                    .map(([key, value]) => (
                                      <div key={key} className="p-2 bg-white rounded border border-green-100">
                                        <div className="font-medium text-gray-700 flex items-center">
                                          <span className="text-green-600 mr-1">✓</span>
                                          {key.replace(/_/g, ' ')}
                                        </div>
                                        {value.task && (
                                          <div className="text-gray-600 mt-1 text-xs italic">Task: {value.task}</div>
                                        )}
                                        {value.operations && value.operations.length > 0 && (
                                          <ul className="list-disc ml-5 mt-1 text-gray-500 space-y-0.5">
                                            {value.operations.map((op, i) => (
                                              <li key={i} className="text-xs">{op}</li>
                                            ))}
                                          </ul>
                                        )}
                                        
                                        {/* Show sources if available */}
                                        {((value.sources && value.sources.length > 0) || (value.results && value.results.length > 0)) && (
                                          <div className="mt-2 border-t border-gray-100 pt-1">
                                            <div className="font-medium text-gray-600 mt-1 mb-1 text-xs">Sources Found:</div>
                                            <div className="space-y-1 ml-1 max-h-60 overflow-y-auto pr-1" style={{ scrollbarWidth: 'thin' }}>
                                              {value.sources?.map((source, i) => (
                                                <div key={`source-${i}`} className="bg-gray-50 p-1 rounded text-xs flex flex-col">
                                                  <a 
                                                    href={source.url || "#"} 
                                                    target="_blank" 
                                                    rel="noopener noreferrer"
                                                    className="text-blue-600 hover:underline text-xs"
                                                  >
                                                    {source.title || source.url || `Source ${i+1}`}
                                                  </a>
                                                  {source.description && (
                                                    <span className="text-gray-500 text-xs italic line-clamp-1">{source.description}</span>
                                                  )}
                                                </div>
                                              ))}
                                              {value.results?.map((result, i) => (
                                                <div key={`result-${i}`} className="bg-gray-50 p-1 rounded text-xs flex flex-col">
                                                  <a 
                                                    href={result.url || result.link || "#"} 
                                                    target="_blank" 
                                                    rel="noopener noreferrer"
                                                    className="text-blue-600 hover:underline text-xs"
                                                  >
                                                    {result.title || result.url || result.link || `Result ${i+1}`}
                                                  </a>
                                                  {(result.snippet || result.description) && (
                                                    <span className="text-gray-500 text-xs italic line-clamp-1">
                                                      {result.snippet || result.description}
                                                    </span>
                                                  )}
                                                </div>
                                              ))}
                                            </div>
                                          </div>
                                        )}
                                      </div>
                                    ))}
                                </div>
                              </div>
                            )}

                            {/* Show subtask details */}
                            {step === 'subtask_completed' && (
                              <div className="mt-2">
                                {Object.entries(detail).filter(([key]) => key !== 'message').map(([key, value]) => (
                                  <div key={key} className="p-2 bg-purple-50 rounded border border-purple-100 text-xs mt-2">
                                    <div className="font-medium text-purple-700">{key} completed</div>
                                    <div className="text-gray-600 mt-1">{value.status}</div>
                                  </div>
                                ))}
                              </div>
                            )}
                            
                            {/* Add a timestamp if available */}
                            {detail && detail.timestamp && (
                              <div className="text-xs text-gray-400 mt-2 text-right">
                                {new Date(detail.timestamp * 1000).toLocaleTimeString()}
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </div>
              </div>

              {/* Raw metadata for developers */}
              <div className="mt-6 border-t pt-4">
                <details className="text-xs">
                  <summary className="cursor-pointer text-blue-600 hover:text-blue-800 font-medium">
                    Show Raw Processing Data (Developer View)
                  </summary>
                  <pre className="mt-2 p-3 bg-gray-800 text-gray-200 rounded-md overflow-x-auto whitespace-pre-wrap text-xs" style={{ maxHeight: '200px' }}>
                    {JSON.stringify(detailsModal.data, null, 2)}
                  </pre>
                </details>
              </div>
            </div>
            
            <div className="p-3 bg-gray-50 border-t sticky bottom-0">
              <button 
                className="w-full py-2 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-md transition"
                onClick={hideModal}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
      
      <div className="flex w-full h-full max-w-screen-xl mx-auto bg-white shadow-2xl overflow-hidden rounded-xl">
        <div className="flex flex-1 flex-col">
          {/* Header */}
          <header className="bg-white p-4 flex justify-between items-center border-b border-gray-200 flex-shrink-0">
            <h1 className="text-xl sm:text-2xl font-bold text-gray-800">GenAI Research Assistant</h1>
            <div className="space-x-2 flex items-center">
              <button
                onClick={() => setShowHistory(prev => !prev)}
                className={`p-2 rounded-full transition duration-300 ease-in-out ${showHistory ? 'bg-blue-600 text-white shadow-md' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'} focus:outline-none focus:ring-2 focus:ring-blue-500`}
                title={showHistory ? 'Hide History' : 'Show History'}
                aria-label={showHistory ? 'Hide Conversation History' : 'Show Conversation History'}
              >
                <History size={20} />
              </button>
              <button
                onClick={() => setShowQuickActions(prev => !prev)}
                className={`p-2 rounded-full transition duration-300 ease-in-out ${showQuickActions ? 'bg-blue-600 text-white shadow-md' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'} focus:outline-none focus:ring-2 focus:ring-blue-500`}
                title={showQuickActions ? 'Hide Quick Actions' : 'Show Quick Actions'}
                aria-label={showQuickActions ? 'Hide Quick Actions Sidebar' : 'Show Quick Actions Sidebar'}
              >
                <Lightbulb size={20} />
              </button>
            </div>
          </header>

          {/* Main chat and sidebar area */}
          <div className="flex flex-1 overflow-hidden">
            {/* History Sidebar */}
            <div
              className={`bg-gray-50 border-r border-gray-200 flex-shrink-0 transition-all duration-300 ease-in-out ${showHistory ? 'w-64 opacity-100' : 'w-0 opacity-0 overflow-hidden'}`}
            >
              <div className="flex flex-col h-full">
                {/* Sidebar header with refresh button */}
                <div className="flex flex-col p-4 border-b border-gray-200">
                  <div className="flex justify-between items-center">
                    <div className="flex items-center">
                      <h2 className="text-lg font-medium text-gray-700">Conversations</h2>
                      <span className="ml-2 text-xs text-gray-500">
                        {isLoadingHistory ? '(Loading...)' : `(${chatHistory.length})`}
                      </span>
                    </div>
                    <button 
                      onClick={() => refreshHistory(true)}
                      className={`flex items-center text-blue-600 hover:text-blue-800 focus:outline-none px-2 py-1 rounded hover:bg-blue-50 ${
                        isLoadingHistory ? 'opacity-70' : ''
                      }`}
                      title="Refresh conversation history and fix timestamps"
                      disabled={isLoadingHistory}
                    >
                      <RefreshCw size={14} className={isLoadingHistory ? 'animate-spin mr-1' : 'mr-1'} />
                      <span className="text-xs font-medium">Refresh</span>
                    </button>
                  </div>
                </div>
                
                <div className="p-4 border-b border-gray-200">
                  <button
                    onClick={() => {
                      // Clear current conversation
                      setCurrentConversationId(null);
                      setIsNewSession(true);
                      setMessages([{
                        role: 'assistant',
                        content: 'Welcome to the GenAI Research Assistant! How can I help with your research today?',
                        id: Date.now()
                      }]);
                      // Clear input
                      setInput('');
                    }}
                    className="w-full bg-blue-600 hover:bg-blue-700 text-white py-2 px-4 rounded-md flex items-center justify-center text-sm font-medium transition-colors"
                  >
                    <span className="mr-1">+</span> New Conversation
                  </button>
                </div>
                
                {/* Search filter for conversations */}
                {chatHistory.length > 0 && (
                  <div className="px-4 pt-3 pb-2">
                    <div className="relative">
                      <input
                        type="text"
                        placeholder="Search conversations..."
                        value={historyFilter}
                        onChange={(e) => setHistoryFilter(e.target.value)}
                        className="w-full py-1.5 pl-3 pr-8 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                      />
                      {historyFilter && (
                        <button
                          onClick={() => setHistoryFilter('')}
                          className="absolute right-2 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
                        >
                          ✕
                        </button>
                      )}
                    </div>
                  </div>
                )}
                
                {/* Scrollable conversation list with loading indicator */}
                <div className="flex-1 overflow-y-auto p-4" style={{ 
                  scrollbarWidth: 'thin',
                  scrollbarColor: '#CBD5E0 #EDF2F7'
                }}>
                  {isLoadingHistory ? (
                    <div className="flex justify-center items-center h-full">
                      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
                    </div>
                  ) : chatHistory.length === 0 ? (
                    <div className="flex flex-col items-center justify-center h-full text-center py-8">
                      <p className="text-gray-500 text-sm italic mb-2">No history yet.</p>
                      <p className="text-gray-400 text-xs">Start a conversation to see it here!</p>
                    </div>
                  ) : (
                    <>
                      <div className="flex justify-between items-center mb-3">
                        <span className="text-xs text-gray-500">
                          {chatHistory.length} conversation{chatHistory.length !== 1 ? 's' : ''}
                        </span>
                      </div>
                      
                      {/* Filtered conversations list */}
                      <div className="space-y-3">
                        {chatHistory
                          .filter(conv => 
                            historyFilter === '' || 
                            (conv.displayTitle || conv.title || "").toLowerCase().includes(historyFilter.toLowerCase())
                          )
                          // No need to sort again - the list is already sorted by our helper functions
                          .map(conv => renderConversationItem(conv))}
                      </div>
                      
                      {/* No results from filter */}
                      {historyFilter && !chatHistory.filter(conv => 
                        (conv.displayTitle || conv.title || "").toLowerCase().includes(historyFilter.toLowerCase())
                      ).length && (
                        <div className="text-center py-8">
                          <p className="text-gray-500 text-sm">No matching conversations found.</p>
                          <button 
                            onClick={() => setHistoryFilter('')}
                            className="text-blue-600 hover:text-blue-800 text-xs mt-2"
                          >
                            Clear filter
                          </button>
                        </div>
                      )}
                    </>
                  )}
                </div>
              </div>
            </div>

            {/* Chat Area - Fixed layout with proper message scroll area */}
            <div className="flex-1 flex flex-col bg-gray-100 overflow-hidden">
              {/* Error Message */}
              {errorMessage && (
                <div className={`${errorMessage.startsWith('Success:') 
                  ? 'bg-green-100 border-l-4 border-green-500 text-green-700' 
                  : 'bg-red-100 border-l-4 border-red-500 text-red-700'} 
                  p-3 mx-4 mt-2 shadow-sm`}>
                  <p className="text-sm">{errorMessage}</p>
                </div>
              )}
              
              {/* Messages Container - Will scroll */}
              <div className="flex-1 overflow-y-auto p-6 pl-12 pr-4 md:pl-16 md:pr-6">
                <div className="space-y-6 w-full flex flex-col">
                  {messages.map((msg, index) => {
                    const isShortMessage = msg.role === 'user' && msg.content.length < 20;
                    return (
                      <div
                        key={msg.id || index}
                        className={`p-4 rounded-xl break-words shadow relative group ${
                          msg.role === 'user'
                          ? `bg-blue-600 text-white ml-auto rounded-br-lg rounded-tl-lg ${isShortMessage ? 'w-auto' : 'max-w-md'} self-end`
                          : msg.isError ? 'bg-red-200 text-red-800 mr-auto rounded-bl-lg rounded-tr-lg border border-red-300 max-w-2xl self-start' 
                          : 'bg-white text-gray-800 mr-auto rounded-bl-lg rounded-tr-lg border border-gray-200 max-w-2xl self-start'
                        }`}
                      >
                        {/* Message content */}
                        {msg.role === 'user' ? (
                          <p style={{ whiteSpace: 'pre-wrap' }}>{msg.content}</p>
                        ) : (
                          renderFormattedMessage(msg.content)
                        )}
                        
                        {/* Display sources if available */}
                        {msg.role === 'assistant' && (() => {
                          const sources = getSources(msg);
                          console.log("Sources for message:", msg.id, sources, "Message data:", msg);
                          
                          // Group sources by type
                          const academicSources = sources.filter(s => s.type === 'academic');
                          const webSources = sources.filter(s => s.type !== 'academic');
                          
                          return sources.length > 0 ? (
                            <div className="mt-3 pt-2 border-t border-gray-100">
                              <div className="flex items-center mb-1">
                                <span className="text-xs font-medium text-gray-600">Sources:</span>
                                <span className="text-xs text-gray-500 ml-1">({sources.length})</span>
                                
                                {/* Show breakdown if there are different types */}
                                {academicSources.length > 0 && webSources.length > 0 && (
                                  <span className="text-xs text-gray-500 ml-1">
                                    ({academicSources.length} academic, {webSources.length} web)
                                  </span>
                                )}
                              </div>
                              
                              {/* Academic sources first */}
                              {academicSources.length > 0 && (
                                <div className="mb-2">
                                  <div className="flex items-center">
                                    <span className="text-xs font-medium text-purple-600 mb-1">Academic Papers</span>
                                  </div>
                                  <div className="space-y-2 max-h-32 overflow-y-auto pr-1" style={{ scrollbarWidth: 'thin' }}>
                                    {academicSources.map((source, i) => (
                                      <div key={`academic-${i}`} className="text-xs bg-purple-50 p-2 rounded border border-purple-100 hover:bg-purple-100 transition-colors">
                                        <a 
                                          href={source.url || "#"} 
                                          target="_blank" 
                                          rel="noopener noreferrer"
                                          className="text-blue-600 hover:underline flex items-start font-medium"
                                        >
                                          <span className="text-xs mr-1.5 text-purple-500">🔬</span>
                                          <span className="truncate font-medium">
                                            {source.title || source.url || `Source ${i+1}`}
                                          </span>
                                        </a>
                                        {source.arxiv_id && (
                                          <div className="ml-5 mt-1 text-purple-600 text-xs">
                                            arXiv: {source.arxiv_id}
                                          </div>
                                        )}
                                        {source.description && (
                                          <p className="text-gray-600 text-xs mt-1 ml-5 line-clamp-2" title={source.description}>
                                            {source.description}
                                          </p>
                                        )}
                                        {source.authors && source.authors.length > 0 && (
                                          <p className="text-purple-500 text-xs mt-1 ml-5">
                                            <span className="font-medium">Authors:</span> {source.authors.slice(0, 3).join(', ')}{source.authors.length > 3 ? '...' : ''}
                                          </p>
                                        )}
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              )}
                              
                              {/* Web sources second */}
                              {webSources.length > 0 && (
                                <div>
                                  {academicSources.length > 0 && (
                                    <div className="flex items-center">
                                      <span className="text-xs font-medium text-blue-600 mb-1">Web Sources</span>
                                    </div>
                                  )}
                                  <div className="space-y-2 max-h-32 overflow-y-auto pr-1" style={{ scrollbarWidth: 'thin' }}>
                                    {webSources.map((source, i) => (
                                      <div key={`web-${i}`} className="text-xs bg-gray-50 p-1.5 rounded border border-gray-100 hover:bg-gray-100 transition-colors">
                                        <a 
                                          href={source.url || "#"} 
                                          target="_blank" 
                                          rel="noopener noreferrer"
                                          className="text-blue-600 hover:underline flex items-start font-medium"
                                        >
                                          <span className="text-xs mr-1.5 text-blue-500">🔗</span>
                                          <span className="truncate">
                                            {source.title || source.url || `Source ${i+1}`}
                                          </span>
                                        </a>
                                        {source.description && (
                                          <p className="text-gray-500 text-xs mt-1 ml-5 line-clamp-2" title={source.description}>
                                            {source.description}
                                          </p>
                                        )}
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              )}
                            </div>
                          ) : null;
                        })()}
                        
                        {/* Show processing info for assistant messages that have processing status */}
                        {msg.role === 'assistant' && msg.processingStatus && !isLoading && (
                          <div className="mt-3 pt-2 border-t border-gray-100 text-xs text-gray-400">
                            <div className="flex items-center justify-between">
                              <div className="flex items-center">
                                <span className="mr-1" role="img" aria-label="Processing info">⚙️</span>
                                <span>
                                  {msg.processingStatus.steps_completed?.includes('execution_completed') ? 
                                    `Used ${getSources(msg).length} sources` : 
                                    'Processing completed'}
                                </span>
                                <span 
                                  className="ml-2 text-blue-500 cursor-pointer hover:underline"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    showProcessingDetails(msg.processingStatus);
                                  }}
                                >
                                  Details
                                </span>
                              </div>
                              {/* Show context information if available */}
                              {msg.metadata && (msg.metadata.context_size || msg.metadata.total_conversation_messages) && (
                                <span className="text-gray-400">
                                  Context: {msg.metadata.context_size || 0} of {msg.metadata.total_conversation_messages || 0} messages
                                </span>
                              )}
                            </div>
                          </div>
                        )}
                        
                        {/* Message action buttons - moved to bottom right */}
                        <div className="absolute bottom-2 right-2 flex space-x-1 opacity-0 group-hover:opacity-100 hover:opacity-100 transition-opacity">
                          {/* Copy button for both message types */}
                          <button
                            onClick={() => {
                              navigator.clipboard.writeText(msg.content);
                              // Optional: Add toast/notification that content was copied
                            }}
                            className={`p-1.5 rounded-full ${
                              msg.role === 'user' 
                                ? 'bg-blue-700 hover:bg-blue-600 text-white' 
                                : 'bg-gray-200 hover:bg-gray-300 text-gray-700'
                            } transition-colors`}
                            title="Copy message"
                          >
                            <Copy size={14} />
                          </button>
                          
                          {/* User message: Stop button - only show when loading */}
                          {msg.role === 'user' && isLoading && !isCancelled && (
                            <button
                              onClick={cancelProcessing}
                              className="p-1.5 rounded-full bg-blue-700 hover:bg-blue-600 text-white transition-colors"
                              title="Stop processing"
                            >
                              <StopCircle size={14} />
                            </button>
                          )}
                          
                          {/* AI message: Retry button */}
                          {msg.role === 'assistant' && !isLoading && !regeneratingMessage && (
                            <button
                              onClick={handleRegenerateResponse}
                              className="p-1.5 rounded-full bg-gray-200 hover:bg-gray-300 text-gray-700 transition-colors"
                              title="Regenerate response"
                              disabled={isLoading || regeneratingMessage}
                            >
                              <RefreshCw size={14} />
                            </button>
                          )}
                        </div>
                      </div>
                    );
                  })}
                  
                  {/* Loading indicator with processing status */}
                  {renderLoadingIndicator()}
                  
                  <div ref={messagesEndRef} />
                </div>
              </div>

              {/* Input Area - Fixed at the bottom */}
              <div className="p-4 border-t border-gray-200 bg-white">
                {currentConversationId && (
                  <div className="mb-2 text-xs flex items-center text-blue-600">
                    <span className="mr-1 w-2 h-2 bg-blue-500 rounded-full"></span>
                    <span className="font-medium truncate max-w-[calc(100%-80px)]" 
                       title={chatHistory.find(c => c.id === currentConversationId)?.displayTitle || 
                             chatHistory.find(c => c.id === currentConversationId)?.title || 
                             'Current conversation'}>
                      {chatHistory.find(c => c.id === currentConversationId)?.displayTitle || 
                       chatHistory.find(c => c.id === currentConversationId)?.title || 
                       'Current conversation'}
                    </span>
                    {!isNewSession && (
                      <button 
                        onClick={() => {
                          // Clear current conversation and start a new one
                          setCurrentConversationId(null);
                          setIsNewSession(true);
                          setMessages([{
                            role: 'assistant',
                            content: 'Starting a new conversation. How can I help with your research?',
                            id: Date.now()
                          }]);
                          setInput('');
                        }}
                        className="ml-2 text-xs text-gray-500 hover:text-blue-600"
                        title="Start a new conversation"
                      >
                        (New)
                      </button>
                    )}
                  </div>
                )}
                <div className="flex items-end bg-gray-100 rounded-xl border border-gray-300 overflow-hidden pr-2 shadow-inner focus-within:border-blue-500 focus-within:ring-1 focus-within:ring-blue-500 transition duration-200">
                  <textarea
                    ref={textareaRef}
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyPress={handleKeyPress}
                    className="flex-1 bg-transparent p-3 text-gray-800 resize-none outline-none placeholder-gray-500"
                    placeholder="Ask me anything about research papers..."
                    rows="1"
                    style={{ minHeight: '48px', maxHeight: '200px' }}
                  />
                  <div className="flex space-x-1 pb-1 pl-1 self-end">
                    <button
                      onClick={isRecording ? stopRecording : startRecording}
                      className={`p-2 rounded-full transition duration-200 ${isRecording ? 'bg-red-600 text-white animate-pulse' : 'bg-gray-200 text-gray-600 hover:bg-gray-300'} disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-red-500`}
                      title={isRecording ? "Stop recording" : "Start voice input"}
                      disabled={isLoading}
                      aria-label={isRecording ? "Stop voice recording" : "Start voice recording"}
                    >
                      <Mic size={20} />
                    </button>
                    <button
                      onClick={generatePrompt}
                      disabled={isGeneratingPrompt || isLoading || !input.trim()}
                      className={`p-2 rounded-full ${
                        isGeneratingPrompt 
                          ? 'bg-yellow-500 text-yellow-100 animate-pulse' 
                          : (!input.trim() ? 'bg-gray-300 text-gray-500 cursor-not-allowed' : 'bg-yellow-400 text-yellow-900 hover:bg-yellow-500')
                      } disabled:opacity-50 transition duration-200 focus:outline-none focus:ring-2 focus:ring-yellow-300`}
                      title={!input.trim() 
                        ? "Enter text first to enhance" 
                        : (isGeneratingPrompt 
                            ? "Enhancing your research query..." 
                            : "Enhance this prompt for more precise research results")}
                      aria-label={isGeneratingPrompt ? "Enhancing research query..." : "Enhance research query for better results"}
                    >
                      <Lightbulb size={20} />
                    </button>
                    <button
                      onClick={sendMessage}
                      disabled={isLoading || !input.trim()}
                      className="p-2 rounded-full bg-blue-600 text-white hover:bg-blue-700 disabled:bg-blue-300 disabled:text-gray-100 transition duration-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
                      title="Send Message"
                      aria-label="Send message"
                    >
                      <Send size={20} />
                    </button>
                  </div>
                </div>
              </div>
            </div>

            {/* Quick Actions Sidebar */}
            <div
              className={`bg-gray-50 border-l border-gray-200 overflow-y-auto flex-shrink-0 transition-all duration-300 ease-in-out ${showQuickActions ? 'w-64 min-w-[16rem] opacity-100 p-4' : 'w-0 opacity-0 p-0 overflow-hidden'}`}
            >
              <div>
                <h2 className="text-lg font-semibold mb-4 text-gray-700">Quick Actions</h2>

                <div className="mb-6">
                  <h3 className="font-medium mb-3 text-gray-600">Tags</h3>
                  <div className="flex flex-wrap -m-1">
                    {quickActions.tags.map(tag => (
                      <button
                        key={tag}
                        onClick={() => handleQuickAction(tag)}
                        className="m-1 bg-green-100 hover:bg-green-200 text-green-800 font-medium py-1 px-3 rounded-full text-sm transition duration-200 focus:outline-none focus:ring-2 focus:ring-green-300"
                      >
                        {tag}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="mb-6">
                  <h3 className="font-medium mb-3 text-gray-600">Domains</h3>
                  <div className="flex flex-wrap -m-1">
                    {quickActions.domains.map(domain => (
                      <button
                        key={domain}
                        onClick={() => handleQuickAction(domain)}
                        className="m-1 bg-purple-100 hover:bg-purple-200 text-purple-800 font-medium py-1 px-3 rounded-full text-sm transition duration-200 focus:outline-none focus:ring-2 focus:ring-purple-300"
                      >
                        {domain}
                      </button>
                    ))}
                  </div>
                </div>

                <div>
                  <h3 className="font-medium mb-3 text-gray-600">Prompt Templates</h3>
                  <button
                    onClick={() => handleQuickAction("Summarize the following concept: ")}
                    className="m-1 bg-yellow-100 hover:bg-yellow-200 text-yellow-800 font-medium py-1.5 px-3 rounded-full text-sm transition duration-200 focus:outline-none focus:ring-2 focus:ring-yellow-300"
                  >
                    Summarize
                  </button>
                  <button
                    onClick={() => handleQuickAction("Compare these research methods: ")}
                    className="m-1 bg-yellow-100 hover:bg-yellow-200 text-yellow-800 font-medium py-1.5 px-3 rounded-full text-sm transition duration-200 focus:outline-none focus:ring-2 focus:ring-yellow-300"
                  >
                    Compare
                    </button>
                  <button
                    onClick={() => handleQuickAction("Explain this concept in simple terms: ")}
                    className="m-1 bg-yellow-100 hover:bg-yellow-200 text-yellow-800 font-medium py-1.5 px-3 rounded-full text-sm transition duration-200 focus:outline-none focus:ring-2 focus:ring-yellow-300"
                  >
                    Simplify
                  </button>
                  <button
                    onClick={() => handleQuickAction("Analyze this following concept: ")}
                    className="m-1 bg-yellow-100 hover:bg-yellow-200 text-yellow-800 font-medium py-1.5 px-3 rounded-full text-sm transition duration-200 focus:outline-none focus:ring-2 focus:ring-yellow-300"
                  >
                    Analyze
                  </button>
                </div>

                <div className="mt-6">
                  <h3 className="font-medium mb-3 text-gray-600">Recommendations</h3>
                  
                  {/* Recommendation filters */}
                  {quickActions.recommendationTags && quickActions.recommendationTags.length > 0 && (
                    <div className="mb-3 flex flex-wrap -m-1">
                      <button
                        onClick={() => filterRecommendationsByTag(null)}
                        className={`m-1 py-1 px-2.5 rounded-full text-xs transition duration-200 focus:outline-none focus:ring-2 focus:ring-blue-300 ${
                          !activeRecommendationTag 
                            ? 'bg-blue-600 text-white' 
                            : 'bg-gray-200 text-gray-800 hover:bg-gray-300'
                        }`}
                      >
                        All
                      </button>
                      {quickActions.recommendationTags.map(tag => (
                        <button
                          key={tag}
                          onClick={() => filterRecommendationsByTag(tag)}
                          className={`m-1 py-1 px-2.5 rounded-full text-xs transition duration-200 focus:outline-none focus:ring-2 focus:ring-blue-300 ${
                            activeRecommendationTag === tag 
                              ? 'bg-blue-600 text-white' 
                              : 'bg-gray-200 text-gray-800 hover:bg-gray-300'
                          }`}
                        >
                          {tag.charAt(0).toUpperCase() + tag.slice(1)}
                        </button>
                      ))}
                    </div>
                  )}
                  
                  {/* Recommendations list */}
                  <div className="max-h-64 overflow-y-auto pr-1 space-y-3">
                    {getFilteredRecommendations().length > 0 ? (
                      getFilteredRecommendations().map((recommendation, index) => (
                        <div key={index} className="bg-white p-3 rounded-md shadow-sm border border-gray-100 transition-all hover:shadow-md">
                          <div className="flex items-start">
                            <div className="flex-1">
                              <h4 className="font-semibold text-sm text-gray-800">{recommendation.title}</h4>
                              {recommendation.type && (
                                <span className="inline-block mt-1 mb-1 bg-blue-100 text-blue-800 text-xs px-2 py-0.5 rounded-full">
                                  {recommendation.type}
                                </span>
                              )}
                              <p className="text-xs text-gray-600 line-clamp-2 mt-1">{recommendation.description}</p>
                              <div className="mt-2 flex items-center justify-between">
                                <button
                                  className="text-blue-600 text-xs font-medium hover:underline transition duration-150 focus:outline-none focus:ring-1 focus:ring-blue-400"
                                  onClick={() => handleQuickAction(`Tell me about ${recommendation.title}`)}
                                >
                                  Learn More
                                </button>
                                {recommendation.relevance_score && (
                                  <span className="text-xs text-gray-500">
                                    {Math.round(recommendation.relevance_score * 100)}% relevant
                                  </span>
                                )}
                              </div>
                            </div>
                          </div>
                        </div>
                      ))
                    ) : recommendations.length === 0 ? (
                      <div className="text-center p-3 text-sm text-gray-500">
                        {messages.length <= 1 
                          ? "Start a conversation to get personalized research recommendations"
                          : "No recommendations available yet"}
                      </div>
                    ) : (
                      <div className="text-center p-3 text-sm text-gray-500">
                        No {activeRecommendationTag} recommendations found
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App; 
