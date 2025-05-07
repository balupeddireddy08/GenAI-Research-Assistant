import React, { useState, useEffect, useRef } from 'react';
import { Mic, Send, Lightbulb, History, FileText } from 'lucide-react';

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

  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);

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

    setMessages(prev => [...prev, { ...userMessage, id: messageId }]);
    setInput('');
    setIsLoading(true);

    try {
      setTimeout(() => {
        const botResponseContent = `This is a mock response for: "${userMessage.content}".\n\nIn a production environment, this would be connected to a backend API that processes your query and returns relevant research information.\n\nHere's some simulated data:\n- Result 1: [Link to Paper 1]\n- Result 2: [Link to Paper 2]\n- Summary: Brief summary of findings.`;
        const botResponse = {
          role: 'assistant',
          content: botResponseContent,
          id: Date.now() + 1
        };

        setMessages(prevMessages => {
          const updatedMessages = [...prevMessages, botResponse];

          const newConversation = {
            id: Date.now(),
            title: userMessage.content.slice(0, 30) + (userMessage.content.length > 30 ? '...' : ''),
            timestamp: new Date().toISOString(),
            messages: updatedMessages
          };
          setChatHistory(prevHistory => [newConversation, ...prevHistory]);

          setIsLoading(false);
          return updatedMessages;
        });

      }, 1000 + Math.random() * 1000);
    } catch (error) {
      console.error("Error sending message:", error);
      setIsLoading(false);
      setMessages(prev => [...prev, { role: 'assistant', content: 'Error processing your request.', isError: true, id: Date.now() }]);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const generatePrompt = () => {
    if (isGeneratingPrompt) return;
    setIsGeneratingPrompt(true);
    setTimeout(() => {
      const generatedPrompt = "Analyze the relationship between transformer architecture developments and performance improvements in natural language understanding tasks";
      setInput(generatedPrompt);
      setIsGeneratingPrompt(false);
      if (textareaRef.current) {
        textareaRef.current.focus();
      }
    }, 1500);
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

  const loadConversation = (conversation) => {
    setMessages(conversation.messages);
  };

  return (
    <div className="flex h-screen w-full bg-gradient-to-br from-blue-50 to-purple-50">
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
              className={`bg-gray-50 border-r border-gray-200 overflow-y-auto flex-shrink-0 transition-all duration-300 ease-in-out ${showHistory ? 'w-64 opacity-100 p-4' : 'w-0 opacity-0 p-0 overflow-hidden'}`}
            >
              <div>
                <h2 className="text-lg font-semibold mb-4 text-gray-700">Conversation History</h2>
                {chatHistory.length === 0 ? (
                  <p className="text-gray-500 text-sm italic">No history yet. Start a conversation!</p>
                ) : (
                  <div className="space-y-3">
                    {chatHistory.map(conv => (
                      <button
                        key={conv.id}
                        onClick={() => loadConversation(conv)}
                        className="w-full text-left p-3 bg-white rounded-md shadow-sm hover:bg-blue-50 cursor-pointer transition duration-150 border border-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-300"
                      >
                        <p className="font-medium text-gray-800 text-sm truncate">{conv.title}</p>
                        <p className="text-xs text-gray-500 mt-1">
                          {new Date(conv.timestamp).toLocaleString()}
                        </p>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Chat Area - Fixed layout with proper message scroll area */}
            <div className="flex-1 flex flex-col bg-gray-100">
              {/* Messages Container - Will scroll */}
              <div className="flex-1 overflow-y-auto p-6">
                <div className="space-y-6">
                  {messages.map((msg, index) => (
                    <div
                      key={msg.id || index}
                      className={`p-4 rounded-xl max-w-md break-words shadow ${
                        msg.role === 'user'
                        ? 'bg-blue-600 text-white ml-auto rounded-br-lg rounded-tl-lg'
                        : msg.isError ? 'bg-red-200 text-red-800 mr-auto rounded-bl-lg rounded-tr-lg border border-red-300'
                        : 'bg-white text-gray-800 mr-auto rounded-bl-lg rounded-tr-lg border border-gray-200'
                      }`}
                    >
                      <p style={{ whiteSpace: 'pre-wrap' }}>{msg.content}</p>
                    </div>
                  ))}
                  {isLoading && (
                    <div className="p-4 rounded-xl bg-white max-w-[60px] mr-auto rounded-bl-lg rounded-tr-lg shadow border border-gray-200">
                      <div className="flex space-x-1">
                        <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce"></div>
                        <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce delay-150"></div>
                        <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce delay-300"></div>
                      </div>
                    </div>
                  )}
                  <div ref={messagesEndRef} />
                </div>
              </div>

              {/* Input Area - Fixed at the bottom */}
              <div className="p-4 border-t border-gray-200 bg-white">
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
                      disabled={isGeneratingPrompt || isLoading}
                      className="p-2 rounded-full bg-yellow-400 text-yellow-900 hover:bg-yellow-500 disabled:opacity-50 transition duration-200 focus:outline-none focus:ring-2 focus:ring-yellow-300"
                      title="Generate Research Prompt"
                      aria-label="Generate a suggested research prompt"
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
              className={`bg-gray-50 border-l border-gray-200 overflow-y-auto flex-shrink-0 transition-all duration-300 ease-in-out ${showQuickActions ? 'w-64 opacity-100 p-4' : 'w-0 opacity-0 p-0 overflow-hidden'}`}
            >
              <div>
                <h2 className="text-lg font-semibold mb-4 text-gray-700">Quick Actions</h2>

                <div className="mb-6">
                  <h3 className="font-medium mb-3 text-gray-600">Latest Research</h3>
                  <div className="flex flex-wrap -m-1">
                    <button
                      onClick={() => handleQuickAction("Find latest AI research")}
                      className="m-1 bg-blue-100 hover:bg-blue-200 text-blue-800 font-medium py-1.5 px-3 rounded-full text-sm transition duration-200 focus:outline-none focus:ring-2 focus:ring-blue-300"
                    >
                      Latest AI Research
                    </button>
                    <button
                      onClick={() => handleQuickAction("Find papers published this week")}
                      className="m-1 bg-blue-100 hover:bg-blue-200 text-blue-800 font-medium py-1.5 px-3 rounded-full text-sm transition duration-200 focus:outline-none focus:ring-2 focus:ring-blue-300"
                    >
                      This Week's Papers
                    </button>
                    <button
                      onClick={() => handleQuickAction("Trending research topics in 2025")}
                      className="m-1 bg-blue-100 hover:bg-blue-200 text-blue-800 font-medium py-1.5 px-3 rounded-full text-sm transition duration-200 focus:outline-none focus:ring-2 focus:ring-blue-300"
                    >
                      Trending Topics
                    </button>
                  </div>
                </div>

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
