import React, { useState, useEffect, useRef } from 'react';
import ChatMessage from './components/ChatMessage';
import ChatInput from './components/ChatInput';
import ModelSelector from './components/ModelSelector';
import TypingIndicator from './components/TypingIndicator';
import DebugButton from './components/DebugButton';
import { getModels, sendChatMessage } from './services/api';
import './styles/App.css';

function App() {
  const [messages, setMessages] = useState([
    { role: 'system', content: "Hello! I'm your AI assistant. How can I help you today?" }
  ]);
  const [models, setModels] = useState({});
  const [selectedModel, setSelectedModel] = useState('gpt-4o-mini');
  const [isTyping, setIsTyping] = useState(false);
  
  const messagesEndRef = useRef(null);

  // Load available models on component mount
  useEffect(() => {
    const loadModels = async () => {
      try {
        const modelData = await getModels();
        setModels(modelData.models);
      } catch (error) {
        console.error('Error loading models:', error);
      }
    };
    
    loadModels();
  }, []);

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSendMessage = async (message) => {
    // Add user message to chat
    const updatedMessages = [...messages, { role: 'user', content: message }];
    setMessages(updatedMessages);
    
    // Show typing indicator
    setIsTyping(true);
    
    try {
      // Prepare messages for API
      const apiMessages = updatedMessages.map(msg => ({
        role: msg.role,
        content: msg.content
      }));
      
      // Send message to API
      const response = await sendChatMessage(apiMessages, selectedModel);
      
      // Add assistant response
      setMessages([...updatedMessages, { role: 'assistant', content: response.response }]);
    } catch (error) {
      console.error('Error sending message:', error);
      setMessages([
        ...updatedMessages, 
        { role: 'system', content: `Sorry, there was an error: ${error.message}` }
      ]);
    } finally {
      setIsTyping(false);
    }
  };

  const handleDebugInfo = (debugData) => {
    // Add debug info to messages
    setMessages([
      ...messages,
      { 
        role: 'system', 
        content: `
          Debug Info:
          API Key Set: ${debugData.api_key_set}
          Model: ${debugData.model}
          Messages: ${debugData.state.messages.length}
          ${JSON.stringify(debugData, null, 2)}
        `
      }
    ]);
  };

  return (
    <div className="chat-container">
      <div className="chat-header">
        <h1>AI Chatbot</h1>
        <div className="header-controls">
          <ModelSelector 
            models={models} 
            selectedModel={selectedModel} 
            onSelectModel={setSelectedModel} 
          />
          <DebugButton 
            messages={messages}
            selectedModel={selectedModel}
            onDebugInfo={handleDebugInfo}
          />
        </div>
      </div>
      
      <div className="chat-messages" id="chat-messages">
        {messages.map((msg, index) => (
          <ChatMessage key={index} role={msg.role} content={msg.content} />
        ))}
        {isTyping && <TypingIndicator />}
        <div ref={messagesEndRef} />
      </div>
      
      <ChatInput onSendMessage={handleSendMessage} />
    </div>
  );
}

export default App; 