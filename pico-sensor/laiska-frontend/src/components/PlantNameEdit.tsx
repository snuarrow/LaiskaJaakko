import React, { useState } from "react";
import axios from "axios";
import { API_URL } from "../config";

interface OneLinerProps {
  sensorName: string;
  sensorIndex: number;
}

const PlantNameEdit: React.FC<OneLinerProps> = ({
  sensorName,
  sensorIndex,
}) => {
  const [oneLiner, setOneLiner] = useState<string>("");

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setOneLiner(e.target.value);
  };

  // Handle form submission
  const handleSubmit = async () => {
    try {
      await axios.post(
        API_URL + "/api/v1/sensor_name?sensor_index=" + sensorIndex,
        { newName: oneLiner },
      );
    } catch (error) {
      console.error("Error posting the one-liner:", error);
    }
  };

  return (
    <div>
      <h3>Soil Moisture {sensorIndex + 1}</h3>
      <div className="plantedit">
        <input
          className="plantedit-input"
          type="text"
          value={oneLiner}
          onChange={handleInputChange}
          placeholder={sensorName}
        />
        <button className="toolbar-button" onClick={handleSubmit}>
          Save
        </button>
      </div>
    </div>
  );
};

export default PlantNameEdit;
