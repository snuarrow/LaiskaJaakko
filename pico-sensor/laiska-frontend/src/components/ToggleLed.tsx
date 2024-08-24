import { useState, useEffect } from "react";
import axios from "axios";
import { API_URL } from "../config";

export default function ToggleLed() {
  const [isOn, setIsOn] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    const fetchLedState = async () => {
      try {
        const response = await axios.get(API_URL + "/api/v1/led");
        setIsOn(response.data.value);
        setLoading(false);
      } catch (error) {
        console.error("Error fetching the LED state:", error);
        setLoading(false);
      }
    };

    fetchLedState();
  }, []);

  const handleToggle = async () => {
    const newValue = isOn ? 0 : 1;
    try {
      await axios.post(API_URL + "/api/v1/led", { value: newValue });
      setIsOn(!isOn);
    } catch (error) {
      console.error("Error sending the POST request:", error);
    }
  };

  if (loading) {
    return <div>Loading...</div>;
  }

  return (
    <div className="toggle-wrapper">
      <div className="toggle-container" onClick={handleToggle}>
        <div className={`toggle-slider ${isOn ? "on" : "off"}`}>
          <div className="toggle-knob"></div>
        </div>
      </div>
      <span className="toggle-label">LED Control</span>
    </div>
  );
}
