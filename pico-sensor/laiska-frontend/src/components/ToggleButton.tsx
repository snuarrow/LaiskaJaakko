import React, { useState } from 'react';
import axios from 'axios';

const ToggleButton: React.FC = () => {
  const [isOn, setIsOn] = useState<boolean>(false);
  const handleToggle = async () => {
    const newValue = isOn ? 0 : 1;
    try {
      await axios.post('http://localhost:5123/api/v1/led', { value: newValue });
      setIsOn(!isOn);
    } catch (error) {
      console.error('Error sending the POST request:', error);
    }
  };
  return (
    <div className="toggle-wrapper">
      <div className="toggle-container" onClick={handleToggle}>
        <div className={`toggle-slider ${isOn ? 'on' : 'off'}`}>
          <div className="toggle-knob"></div>
        </div>
      </div>
      <span className="toggle-label">LED Control</span>
    </div>
  );
};

export default ToggleButton;
