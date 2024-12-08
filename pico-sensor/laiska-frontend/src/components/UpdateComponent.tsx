import { useState, useEffect } from "react";
import axios from "axios";
import { API_URL } from "../config";
import ProgressBar from "./ProgressBar";


export default function UpdateComponent() {
  const [updatesAvailable, setUpdatesAvailable] = useState<boolean>(false);
  const [currentVersion, setCurrentVersion] = useState<Number>(0);
  const [remoteVersion, setRemoteVersion] = useState<Number>(0);
  const [downloadOk, setDownloadOk] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(true);
  const [downloading, setDownloading] = useState<boolean>(false);
  const [installing, setInstalling] = useState<boolean>(false);

  const handleReload = () => {
    window.location.reload();
  };

  const handleDownload = async() => {
    try {
      setDownloading(true);
      const response = await axios.post(
        API_URL + "/api/v1/download_firmware"
      )
      setDownloading(false)
      console.log("response", response.data)
      setDownloadOk(response.data.ready)
    } catch (error) {
      console.error("Error initiating cloud update:", error);
      setDownloading(false)
    }
  };

  const handleInstall = async() => {
    try {
      setInstalling(true)
      console.log("initiating install new firmware procedure")
      const response = await axios.post(API_URL + "/api/v1/reset");
      console.log(response)
      const url = API_URL + "/api/v1/health"
      const timeout = 1000;
      const maxRetries = 30;
      const handleReady = async() => {
        for (let i = 0; i < maxRetries; i++) {
          try {
            const response = await axios.get(url, { timeout });
            if (response.status === 200 && response.data?.ok === true) {
              handleReload()
              break
            }
          } catch (error) {

          }
          await new Promise((resolve) => setTimeout(resolve, 1000));
        }
        console.error("update install error")
      }
      setTimeout(handleReady, 2000)
    } catch (error) {
      console.error("error while initiating install procedure")
    }
  }

  useEffect(() => {
      const fetchUpdatesAvailable = async () => {
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
  
      fetchUpdatesAvailable();
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
        {updatesAvailable && !downloading && !downloadOk && (<button onClick={handleDownload}>Download</button>)}
        {downloadOk && !installing && (<button onClick={handleInstall}>Install</button>)}
        {downloading && (<ProgressBar duration={60} description="downloading.."/>)}
        {installing && (<ProgressBar duration={60} description="installing.."/>)}
    </div>
  );
};
