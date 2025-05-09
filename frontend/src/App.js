import React, { useState, useEffect, useRef } from 'react';
import { Mic, Send, Lightbulb, History, X } from 'lucide-react';
import { sendChatMessage, getConversationHistory, getConversation } from './utils/api';

function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isGeneratingPrompt, setIsGeneratingPrompt] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [quickActions] = useState({
    tags: ['AI', 'Machine Learning', 'NLP', 'Computer Vision', 'Robotics'],
    technologies: ['PyTorch', 'TensorFlow', 'Transformers', 'BERT', 'GPT']
  });
  const [chatHistory, setChatHistory] = useState([]);
  const [showHistory, setShowHistory] = useState(true);
  const [showQuickActions, setShowQuickActions] = useState(true);
  const [currentConversationId, setCurrentConversationId] = useState(null);
  const [errorMessage, setErrorMessage] = useState(null);
  const [processingStatus, setProcessingStatus] = useState(null);
  const [detailsModal, setDetailsModal] = useState({ show: false, data: null });
  const [historyFilter, setHistoryFilter] = useState('');

  // Track if this is a new session
  const [isNewSession, setIsNewSession] = useState(true);

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
      try {
        const history = await getConversationHistory();
        console.log("Loaded conversation history:", history);
        setChatHistory(history || []);
      } catch (error) {
        console.error("Error loading conversation history:", error);
        setErrorMessage("Failed to load conversation history. Using local storage only.");
        // Use empty array if history can't be loaded
        setChatHistory([]);
      }
    };

    loadHistory();
  }, []);

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

  const sendMessage = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage = { role: 'user', content: input.trim() };
    const messageId = Date.now();
    setErrorMessage(null);
    setProcessingStatus(null);

    // Add user message to chat
    setMessages(prev => [...prev, { ...userMessage, id: messageId }]);
    setInput('');
    setIsLoading(true);

    try {
      // Log that we're continuing or starting a conversation
      console.log(`${currentConversationId ? 'Continuing conversation' : 'Starting new conversation'}: ${currentConversationId || 'new'}`);
      
      // If this is continuing an existing conversation, also log the number of existing messages
      if (currentConversationId) {
        console.log(`Conversation has ${messages.length} messages in context`);
      }

      // Send message to backend API
      const response = await sendChatMessage(
        userMessage.content, 
        currentConversationId
      );

      console.log("Response received:", response);
      console.log("Processing status:", response.processing_status);
      console.log("Sources in response:", response.sources);
      
      // Update the processing status state
      setProcessingStatus(response.processing_status);

      // Update conversation ID if this is a new conversation
      if (!currentConversationId && response.conversation_id) {
        console.log(`Setting conversation ID to: ${response.conversation_id}`);
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

      // Refresh conversation history
      const history = await getConversationHistory();
      setChatHistory(history);

      setIsLoading(false);
    } catch (error) {
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

  const loadConversation = async (conversation) => {
    try {
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

      console.log(`Loaded ${fullConversation.messages.length} messages from conversation history`);

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

  // Add a visual indicator for the active conversation in the history sidebar
  const renderConversationItem = (conv) => {
    const isActive = conv.id === currentConversationId;
    // Ensure valid date or use current date as fallback
    const updatedDate = conv.updated_at && !isNaN(new Date(conv.updated_at).getTime()) 
      ? new Date(conv.updated_at) 
      : new Date();
    
    return (
      <button
        key={conv.id}
        onClick={() => loadConversation(conv)}
        className={`w-full text-left p-3 rounded-md shadow-sm hover:bg-blue-50 cursor-pointer transition duration-150 border ${
          isActive 
            ? 'border-blue-400 bg-blue-50 shadow-md' 
            : 'border-gray-100 bg-white'
        } focus:outline-none focus:ring-2 focus:ring-blue-300`}
      >
        <p className="font-medium text-gray-800 text-sm truncate flex items-center">
          {isActive && (
            <span className="w-2 h-2 bg-blue-500 rounded-full mr-2 flex-shrink-0" aria-hidden="true"></span>
          )}
          <span className="truncate">{conv.title}</span>
        </p>
        <div className="flex justify-between items-center mt-1">
          <p className="text-xs text-gray-500">
            {updatedDate.toLocaleString()}
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
      if (academicAgent && Array.isArray(academicAgent.sources)) {
        sources.push(...academicAgent.sources);
      }
      
      // Check search_agent results
      const searchAgent = message.processingStatus.detailed_status.search_agent;
      if (searchAgent && Array.isArray(searchAgent.results)) {
        sources.push(...searchAgent.results.map(result => ({
          url: result.url || result.link,
          title: result.title,
          description: result.snippet || result.description
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
              title: result.title,
              description: result.snippet || result.description
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
          description: source.description || source.snippet || null
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
        
        // Handle code blocks
        .replace(/```([^`]+)```/g, '<pre class="bg-gray-100 p-2 rounded my-2 text-sm overflow-x-auto"><code>$1</code></pre>')
        
        // Handle inline code (`code`)
        .replace(/`([^`]+)`/g, '<code class="bg-gray-100 text-red-600 px-1 py-0.5 rounded text-sm">$1</code>');
      
      // Wrap bullet point lists in ul tags - more complex to handle nested content
      // First, identify paragraph breaks
      const paragraphs = processedContent.split('\n\n');
      
      // Process each paragraph separately
      const processedParagraphs = paragraphs.map(para => {
        // If paragraph contains list items
        if (para.includes('<li class="ml-5 text-gray-700 mb-1 list-disc">')) {
          return `<ul class="my-2 list-disc pl-5">${para}</ul>`;
        }
        // Regular paragraph
        return `<p class="mb-3">${para}</p>`;
      });
      
      // Join everything back
      const finalContent = processedParagraphs.join('');
      
      // Return the content with HTML enabled
      return (
        <div
          dangerouslySetInnerHTML={{ __html: finalContent }}
          className="message-content text-gray-800 leading-relaxed"
          style={{ lineHeight: '1.6' }}
        />
      );
    } catch (error) {
      console.error("Error processing markdown:", error);
      // Fallback to plain text if something goes wrong
      return <p style={{ whiteSpace: 'pre-wrap' }}>{content}</p>;
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
                        'planning',
                        'plan_generated',
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
                                        
                                        {/* Show sources/results if available */}
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
                <div className="p-4 border-b border-gray-200">
                  <h2 className="text-lg font-semibold text-gray-700">Conversation History</h2>
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
                
                {/* Scrollable conversation list */}
                <div className="flex-1 overflow-y-auto p-4" style={{ 
                  scrollbarWidth: 'thin',
                  scrollbarColor: '#CBD5E0 #EDF2F7'
                }}>
                  {chatHistory.length === 0 ? (
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
                        <button 
                          className="text-xs text-blue-600 hover:text-blue-800"
                          onClick={() => {
                            // Refresh conversation history
                            getConversationHistory().then(history => {
                              setChatHistory(history || []);
                            }).catch(err => {
                              console.error("Error refreshing history:", err);
                            });
                          }}
                        >
                          Refresh
                        </button>
                      </div>
                      
                      {/* Filtered conversations list */}
                      <div className="space-y-3">
                        {chatHistory
                          .filter(conv => 
                            historyFilter === '' || 
                            conv.title.toLowerCase().includes(historyFilter.toLowerCase())
                          )
                          .sort((a, b) => new Date(b.updated_at || 0) - new Date(a.updated_at || 0))
                          .map(conv => renderConversationItem(conv))}
                      </div>
                      
                      {/* No results from filter */}
                      {historyFilter && !chatHistory.filter(conv => 
                        conv.title.toLowerCase().includes(historyFilter.toLowerCase())
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
                <div className="bg-red-100 border-l-4 border-red-500 text-red-700 p-3 mx-4 mt-2 shadow-sm">
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
                        className={`p-4 rounded-xl break-words shadow ${
                          msg.role === 'user'
                          ? `bg-blue-600 text-white ml-auto rounded-br-lg rounded-tl-lg ${isShortMessage ? 'w-auto' : 'max-w-md'} self-end`
                          : msg.isError ? 'bg-red-200 text-red-800 mr-auto rounded-bl-lg rounded-tr-lg border border-red-300 max-w-2xl self-start' 
                          : 'bg-white text-gray-800 mr-auto rounded-bl-lg rounded-tr-lg border border-gray-200 max-w-2xl self-start'
                        }`}
                      >
                        {msg.role === 'user' ? (
                          <p style={{ whiteSpace: 'pre-wrap' }}>{msg.content}</p>
                        ) : (
                          renderFormattedMessage(msg.content)
                        )}
                        
                        {/* Display sources if available */}
                        {msg.role === 'assistant' && (() => {
                          const sources = getSources(msg);
                          console.log("Sources for message:", msg.id, sources, "Message data:", msg);
                          return sources.length > 0 ? (
                            <div className="mt-3 pt-2 border-t border-gray-100">
                              <div className="flex items-center mb-1">
                                <span className="text-xs font-medium text-gray-600">Sources:</span>
                                <span className="text-xs text-gray-500 ml-1">({sources.length})</span>
                              </div>
                              <div className="space-y-2 max-h-32 overflow-y-auto pr-1" style={{ scrollbarWidth: 'thin' }}>
                                {sources.map((source, i) => (
                                  <div key={i} className={`text-xs ${source.type === 'academic_pdf' ? 'bg-red-50' : 'bg-gray-50'} p-1.5 rounded border ${source.type === 'academic_pdf' ? 'border-red-100' : 'border-gray-100'} hover:bg-gray-100 transition-colors`}>
                                    <a 
                                      href={source.url || "#"} 
                                      target="_blank" 
                                      rel="noopener noreferrer"
                                      className="text-blue-600 hover:underline flex items-start font-medium"
                                    >
                                      {source.type === 'academic' && source.arxiv_id && (
                                        <span className="text-xs mr-1.5 text-purple-500">🔬</span>
                                      )}
                                      {source.type === 'academic_pdf' && (
                                        <span className="text-xs mr-1.5 text-red-500">📄</span>
                                      )}
                                      {source.type !== 'academic' && source.type !== 'academic_pdf' && (
                                        <span className="text-xs mr-1.5 text-blue-500">🔗</span>
                                      )}
                                      <span className="truncate">
                                        {source.title || source.url || `Source ${i+1}`}
                                        {source.arxiv_id && !source.title?.includes(source.arxiv_id) && ` (${source.arxiv_id})`}
                                      </span>
                                    </a>
                                    {source.description && (
                                      <p className="text-gray-500 text-xs mt-1 ml-5 line-clamp-2" title={source.description}>
                                        {source.description}
                                      </p>
                                    )}
                                    {source.authors && source.authors.length > 0 && (
                                      <p className="text-gray-500 text-xs mt-1 ml-5">
                                        <span className="font-medium">Authors:</span> {source.authors.slice(0, 3).join(', ')}{source.authors.length > 3 ? '...' : ''}
                                      </p>
                                    )}
                                  </div>
                                ))}
                              </div>
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
                    <span>Continuing conversation: {chatHistory.find(c => c.id === currentConversationId)?.title || 'Current chat'}</span>
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
                  <h3 className="font-medium mb-3 text-gray-600">Technologies</h3>
                  <div className="flex flex-wrap -m-1">
                    {quickActions.technologies.map(tech => (
                      <button
                        key={tech}
                        onClick={() => handleQuickAction(tech)}
                        className="m-1 bg-purple-100 hover:bg-purple-200 text-purple-800 font-medium py-1 px-3 rounded-full text-sm transition duration-200 focus:outline-none focus:ring-2 focus:ring-purple-300"
                      >
                        {tech}
                      </button>
                    ))}
                  </div>
                </div>

                <div>
                  <h3 className="font-medium mb-3 text-gray-600">Prompt Templates</h3>
                  <button
                    onClick={() => handleQuickAction("Summarize the following paper: ")}
                    className="m-1 bg-yellow-100 hover:bg-yellow-200 text-yellow-800 font-medium py-1.5 px-3 rounded-full text-sm transition duration-200 focus:outline-none focus:ring-2 focus:ring-yellow-300"
                  >
                    Paper Summary
                  </button>
                  <button
                    onClick={() => handleQuickAction("Compare these research methods: ")}
                    className="m-1 bg-yellow-100 hover:bg-yellow-200 text-yellow-800 font-medium py-1.5 px-3 rounded-full text-sm transition duration-200 focus:outline-none focus:ring-2 focus:ring-yellow-300"
                  >
                    Compare Methods
                  </button>
                  <button
                    onClick={() => handleQuickAction("Explain this concept in simple terms: ")}
                    className="m-1 bg-yellow-100 hover:bg-yellow-200 text-yellow-800 font-medium py-1.5 px-3 rounded-full text-sm transition duration-200 focus:outline-none focus:ring-2 focus:ring-yellow-300"
                  >
                    Simplify Concept
                  </button>
                  <button
                    onClick={() => handleQuickAction("Generate a research question about: ")}
                    className="m-1 bg-yellow-100 hover:bg-yellow-200 text-yellow-800 font-medium py-1.5 px-3 rounded-full text-sm transition duration-200 focus:outline-none focus:ring-2 focus:ring-yellow-300"
                  >
                    Research Question
                  </button>
                </div>

                <div className="mt-6">
                  <h3 className="font-medium mb-3 text-gray-600">Recommendations</h3>
                  <div className="space-y-3">
                    <div className="bg-white p-3 rounded-md shadow-sm border border-gray-100">
                      <h4 className="font-semibold text-sm text-gray-800">Attention Is All You Need</h4>
                      <p className="text-xs text-gray-500">Vaswani et al. (2017)</p>
                      <button
                        className="mt-2 text-blue-600 text-xs font-medium hover:underline transition duration-150 focus:outline-none focus:ring-1 focus:ring-blue-400"
                        onClick={() => handleQuickAction("Tell me about the Transformer architecture")}
                      >
                        Learn More
                      </button>
                    </div>
                    <div className="bg-white p-3 rounded-md shadow-sm border border-gray-100">
                      <h4 className="font-semibold text-sm text-gray-800">BERT: Pre-training of Deep Bidirectional Transformers</h4>
                      <p className="text-xs text-gray-500">Devlin et al. (2018)</p>
                      <button
                        className="mt-2 text-blue-600 text-xs font-medium hover:underline transition duration-150 focus:outline-none focus:ring-1 focus:ring-blue-400"
                        onClick={() => handleQuickAction("Explain BERT")}
                      >
                        Learn More
                      </button>
                    </div>
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
