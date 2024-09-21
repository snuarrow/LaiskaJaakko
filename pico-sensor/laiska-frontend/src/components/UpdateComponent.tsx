import { useState, useEffect } from "react";
import axios from "axios";
import { API_URL } from "../config";
import ProgressBar from "./ProgressBar";


export default function UpdateComponent() {
  const [updatesAvailable, setUpdatesAvailable] = useState<boolean>(false);
  const [currentVersion, setCurrentVersion] = useState<Number>(0);
  const [remoteVersion, setRemoteVersion] = useState<Number>(0);
  const [loading, setLoading] = useState<boolean>(true);
  const [updating, setUpdating] = useState<boolean>(false);

  const handleUpdate = async() => {
    try {
      setUpdating(true);
      const response = await axios.post(
        API_URL + "/api/v1/update_firmware"
      )
      console.log("response", response.data)
    } catch (error) {
      console.error("Error initiating cloud update:", error);
    }
  };

  useEffect(() => {
      const fetchLedState = async () => {
        try {
          const response = await axios.get(API_URL + "/api/v1/updates_available");
          console.log("response", response.data)
          setUpdatesAvailable(response.data.updatesAvailable)
          setCurrentVersion(response.data.currentVersion)
          setRemoteVersion(response.data.remoteVersion)
          setLoading(false);
        } catch (error) {
          console.error("Error fetching the update state:", error);
          setLoading(false);
        }
      };
  
      fetchLedState();
    }, []
  );

  if (loading) {
    return (
      <div>
        <h2>Firmware Update:</h2>
        <div>Loading...</div>
      </div>
    )
  }

  return (
    <div>
        <h2>Firmware Update:</h2>
        <div>Updates Available: {updatesAvailable ? "Yes" : "No"}</div>
        <div>Current version: {String(currentVersion)}</div>
        <div>Available version: {String(remoteVersion)}</div>
        {updatesAvailable && !updating && (<button onClick={handleUpdate}>Update</button>)}
        {updating && (<ProgressBar duration={90}/>)}
    </div>
  );
};
