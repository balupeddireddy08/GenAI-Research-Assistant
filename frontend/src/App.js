import React, { useState, useEffect, useRef } from 'react';
// Corrected: Re-added History and FileText for icons
import { Mic, Send, Lightbulb, History, FileText } from 'lucide-react'; 

function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isGeneratingPrompt, setIsGeneratingPrompt] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  // Corrected: Removed setQuickActions as it was unused
  const [quickActions] = useState({ 
    tags: ['AI', 'Machine Learning', 'NLP', 'Computer Vision', 'Robotics'],
    technologies: ['PyTorch', 'TensorFlow', 'Transformers', 'BERT', 'GPT']
  });
  const [chatHistory, setChatHistory] = useState([]);
  const [showHistory, setShowHistory] = useState(true);
  const [showQuickActions, setShowQuickActions] = useState(true);

  const messagesEndRef = useRef(null);

  // Corrected: Added messages.length to the dependency array for scrolling
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth', block: 'end' }); // block: 'end' ensures the very bottom is visible
    }
  }, [messages.length]); 

  // Initial welcome message effect
  useEffect(() => {
    if (messages.length === 0) {
      setMessages([{
        role: 'assistant',
        content: 'Welcome to the GenAI Research Assistant! How can I help with your research today?'
      }]);
    }
  }, []); // This effect runs only once on mount

  const handleQuickAction = (action) => {
    setInput(prev => prev + ` ${action}`);
  };

  const sendMessage = async () => {
    if (!input.trim()) return;

    const userMessage = { role: 'user', content: input };
    
    // Add user message immediately for responsive UI
    setMessages(prev => [...prev, userMessage]); 
    setInput('');
    setIsLoading(true);

    try {
      // Simulate API call delay
      setTimeout(() => {
        const botResponseContent = `This is a mock response for: "${userMessage.content}".\nIn a production environment, this would be connected to a backend API that processes your query and returns relevant research information.`;
        const botResponse = {
          role: 'assistant',
          content: botResponseContent
        };

        // Use functional update to ensure we have the latest state including the user message
        setMessages(prevMessages => {
          const updatedMessages = [...prevMessages, botResponse];

          // Add to chat history with the complete conversation turn
          const newConversation = {
            id: Date.now(),
            title: userMessage.content.slice(0, 30) + (userMessage.content.length > 30 ? '...' : ''),
            timestamp: new Date().toISOString(),
            messages: updatedMessages // Store the complete conversation turn
          };
          setChatHistory(prevHistory => [newConversation, ...prevHistory]);

          setIsLoading(false);
          return updatedMessages; // Return the updated messages array
        });

      }, 1000);
    } catch (error) {
      console.error("Error sending message:", error);
      setIsLoading(false);
      // Optionally add an error message to the chat
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const generatePrompt = () => {
    setIsGeneratingPrompt(true);
    // Simulate prompt generation delay
    setTimeout(() => {
      const generatedPrompt = "Analyze the relationship between transformer architecture developments and performance improvements in natural language understanding tasks";
      setInput(generatedPrompt);
      setIsGeneratingPrompt(false);
    }, 1500);
  };

  const startRecording = () => {
    setIsRecording(true);
    // Simulate recording time
    setTimeout(() => {
      setIsRecording(false);
      setInput(prev => prev + " [Speech converted to text would appear here]");
    }, 2000);
  };

  const stopRecording = () => {
    setIsRecording(false);
    // In a real app, this would stop the audio recording and process the result
    console.log("Recording stopped (simulated).");
  };

  const loadConversation = (conversation) => {
    setMessages(conversation.messages);
  };


  return (
    // Outer container with background and centering flex
    <div className="flex items-center justify-center h-screen bg-gradient-to-br from-blue-100 to-purple-100 p-4"> 
      {/* Main app container with rounded corners and shadow */}
      <div className="flex h-full w-full max-w-7xl bg-white rounded-lg shadow-xl overflow-hidden"> 
        {/* Content area */}
        <div className="flex-1 flex flex-col">
          {/* Header */}
          <header className="bg-white shadow-md p-4 flex justify-between items-center border-b border-gray-200"> 
            <h1 className="text-2xl font-semibold text-gray-800">GenAI Research Assistant</h1> 
            {/* Icon buttons */}
            <div className="space-x-2 flex items-center"> {/* Added flex and items-center for alignment */}
              <button 
                onClick={() => setShowHistory(prev => !prev)} 
                // Styled as a circular icon button
                className={`p-2 rounded-full transition duration-200 ${showHistory ? 'bg-blue-500 text-white' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'}`} 
                title={showHistory ? 'Hide History' : 'Show History'} // Tooltip for accessibility
              >
                <History size={20} />
              </button>
              <button 
                onClick={() => setShowQuickActions(prev => !prev)} 
                 // Styled as a circular icon button
                className={`p-2 rounded-full transition duration-200 ${showQuickActions ? 'bg-blue-500 text-white' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'}`}
                 title={showQuickActions ? 'Hide Quick Actions' : 'Show Quick Actions'} // Tooltip for accessibility
              >
                <FileText size={20} /> {/* Using FileText icon */}
              </button>
            </div>
          </header>

          {/* Main chat and sidebar area */}
          <main className="flex-1 overflow-hidden flex">
            {/* History Sidebar */}
            {showHistory && (
              <div className="w-72 bg-gray-50 border-r border-gray-200 p-4 overflow-y-auto flex-shrink-0"> 
                <h2 className="text-lg font-semibold mb-4 text-gray-700">Conversation History</h2> 
                {chatHistory.length === 0 ? (
                  <p className="text-gray-500 text-sm italic">No history yet. Start a conversation!</p> 
                ) : (
                  <div className="space-y-3"> 
                    {chatHistory.map(conv => (
                      <div 
                        key={conv.id} 
                        className="p-3 bg-white rounded-md shadow-sm hover:bg-blue-50 cursor-pointer transition duration-150 border border-gray-100" 
                        onClick={() => loadConversation(conv)}
                      >
                        <p className="font-medium text-gray-800 text-sm">{conv.title}</p> 
                        <p className="text-xs text-gray-500 mt-1"> 
                          {new Date(conv.timestamp).toLocaleString()}
                        </p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Chat Area */}
            <div className="flex-1 flex flex-col">
              <div className="flex-1 overflow-y-auto p-6 space-y-4"> 
                {messages.map((msg, index) => (
                  <div 
                    key={index} 
                    className={`p-4 rounded-xl max-w-sm break-words ${ 
                      msg.role === 'user' 
                      ? 'bg-blue-600 text-white ml-auto rounded-br-sm' 
                      : 'bg-gray-200 text-gray-800 mr-auto rounded-bl-sm' 
                    }`}
                  >
                    {/* Using pre-wrap to handle newlines correctly */}
                    <p style={{ whiteSpace: 'pre-wrap' }}>{msg.content}</p> 
                  </div>
                ))}
                {isLoading && (
                  <div className="p-4 rounded-xl bg-gray-200 max-w-sm mr-auto rounded-bl-sm"> 
                    <div className="flex space-x-2">
                      <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce"></div>
                      <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce delay-150"></div> 
                      <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce delay-300"></div> 
                    </div>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </div>

              {/* Input Area */}
              <div className="p-4 border-t border-gray-200 bg-white"> 
                <div className="flex items-end bg-gray-100 rounded-lg border border-gray-300 overflow-hidden pr-2"> 
                  <textarea
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyPress={handleKeyPress}
                    className="flex-1 bg-transparent p-3 focus:outline-none resize-none text-gray-700" 
                    placeholder="Ask me anything about research papers..."
                    rows="1" 
                    style={{ minHeight: '40px', maxHeight: '160px' }} 
                  />
                  {/* Buttons */}
                  <div className="flex space-x-1 pb-1 pl-1"> 
                    <button
                      onClick={isRecording ? stopRecording : startRecording}
                      className={`p-2 rounded-full ${isRecording ? 'bg-red-500 text-white' : 'bg-gray-300 text-gray-700'} hover:bg-opacity-80 transition duration-200`} 
                      title={isRecording ? "Stop recording" : "Start voice input"}
                    >
                      <Mic size={20} />
                    </button>
                     <button
                      onClick={generatePrompt}
                      disabled={isGeneratingPrompt}
                      className="p-2 rounded-full bg-yellow-400 text-yellow-900 hover:bg-yellow-500 disabled:opacity-50 transition duration-200" 
                      title="Generate Research Prompt"
                    >
                      <Lightbulb size={20} />
                    </button>
                    <button
                      onClick={sendMessage}
                      disabled={isLoading || !input.trim()}
                      className="p-2 rounded-full bg-blue-600 text-white hover:bg-blue-700 disabled:bg-blue-300 disabled:text-gray-100 transition duration-200" 
                      title="Send Message"
                    >
                      <Send size={20} />
                    </button>
                  </div>
                </div>
              </div>
            </div>

            {/* Quick Actions Sidebar */}
            {showQuickActions && (
              <div className="w-72 bg-gray-50 border-l border-gray-200 p-4 overflow-y-auto flex-shrink-0"> 
                <h2 className="text-lg font-semibold mb-4 text-gray-700">Quick Actions</h2> 

                <div className="mb-6">
                  <h3 className="font-medium mb-3 text-gray-600">Latest Research</h3> 
                  {/* Buttons adjusted for consistent styling */}
                  <button 
                    onClick={() => handleQuickAction("Find latest AI research")}
                    className="bg-blue-100 hover:bg-blue-200 text-blue-800 font-medium py-1.5 px-3 rounded-full text-sm mr-2 mb-2 transition duration-200"
                  >
                    Latest AI Research
                  </button>
                  <button 
                    onClick={() => handleQuickAction("Find papers published this week")}
                    className="bg-blue-100 hover:bg-blue-200 text-blue-800 font-medium py-1.5 px-3 rounded-full text-sm mr-2 mb-2 transition duration-200"
                  >
                    This Week's Papers
                  </button>
                  <button 
                    onClick={() => handleQuickAction("Trending research topics in 2025")}
                    className="bg-blue-100 hover:bg-blue-200 text-blue-800 font-medium py-1.5 px-3 rounded-full text-sm mr-2 mb-2 transition duration-200"
                  >
                    Trending Topics
                  </button>
                </div>

                <div className="mb-6">
                  <h3 className="font-medium mb-3 text-gray-600">Tags</h3> 
                  <div className="flex flex-wrap -m-1"> 
                    {quickActions.tags.map(tag => (
                      <button 
                        key={tag} 
                        onClick={() => handleQuickAction(tag)}
                        className="m-1 bg-green-100 hover:bg-green-200 text-green-800 font-medium py-1 px-3 rounded-full text-sm transition duration-200" 
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
                        className="m-1 bg-purple-100 hover:bg-purple-200 text-purple-800 font-medium py-1 px-3 rounded-full text-sm transition duration-200" 
                      >
                        {tech}
                      </button>
                    ))}
                  </div>
                </div>

                <div>
                  <h3 className="font-medium mb-3 text-gray-600">Prompt Templates</h3> 
                   {/* Buttons adjusted for consistent styling */}
                  <button 
                    onClick={() => handleQuickAction("Summarize the following paper: ")}
                    className="bg-yellow-100 hover:bg-yellow-200 text-yellow-800 font-medium py-1.5 px-3 rounded-full text-sm mr-2 mb-2 transition duration-200"
                  >
                    Paper Summary
                  </button>
                  <button 
                    onClick={() => handleQuickAction("Compare these research methods: ")}
                    className="bg-yellow-100 hover:bg-yellow-200 text-yellow-800 font-medium py-1.5 px-3 rounded-full text-sm mr-2 mb-2 transition duration-200"
                  >
                    Compare Methods
                  </button>
                  <button 
                    onClick={() => handleQuickAction("Explain this concept in simple terms: ")}
                    className="bg-yellow-100 hover:bg-yellow-200 text-yellow-800 font-medium py-1.5 px-3 rounded-full text-sm mr-2 mb-2 transition duration-200"
                  >
                    Simplify Concept
                  </button>
                  <button 
                    onClick={() => handleQuickAction("Generate a research question about: ")}
                    className="bg-yellow-100 hover:bg-yellow-200 text-yellow-800 font-medium py-1.5 px-3 rounded-full text-sm mr-2 mb-2 transition duration-200"
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
                        className="mt-2 text-blue-600 text-xs font-medium hover:underline transition duration-150" 
                        onClick={() => handleQuickAction("Tell me about the Transformer architecture")}
                      >
                        Learn More
                      </button>
                    </div>

                    <div className="bg-white p-3 rounded-md shadow-sm border border-gray-100"> 
                      <h4 className="font-semibold text-sm text-gray-800">BERT: Pre-training of Deep Bidirectional Transformers</h4> 
                      <p className="text-xs text-gray-500">Devlin et al. (2018)</p>
                      <button 
                        className="mt-2 text-blue-600 text-xs font-medium hover:underline transition duration-150" 
                        onClick={() => handleQuickAction("Explain BERT")}
                      >
                        Learn More
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </main>
        </div>
      </div>
    </div>
  );
}

export default App;
