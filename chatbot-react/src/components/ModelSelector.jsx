import React from 'react';
import '../styles/ModelSelector.css';

const ModelSelector = ({ models, selectedModel, onSelectModel }) => {
  return (
    <div className="model-selector">
      <label htmlFor="model-select">Model:</label>
      <select 
        id="model-select" 
        value={selectedModel} 
        onChange={(e) => onSelectModel(e.target.value)}
      >
        <option value="gpt-4o-mini">GPT-4o-mini</option>
        {Object.entries(models).map(([id, name]) => {
          // Skip the default model which is already added
          if (id !== 'gpt-4o-mini') {
            return (
              <option key={id} value={id}>
                {name}
              </option>
            );
          }
          return null;
        })}
      </select>
    </div>
  );
};

export default ModelSelector; 