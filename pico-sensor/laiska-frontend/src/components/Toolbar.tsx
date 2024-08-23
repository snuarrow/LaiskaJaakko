import ToggleLed from "./ToggleLed";
import { useState } from "react";
import Popup from "./Popup";

const Toolbar = () => {
  const [isPopupOpen, setIsPopupOpen] = useState(false);

  const togglePopup = () => {
    setIsPopupOpen(!isPopupOpen);
  };
  return (
    <div className="toolbar">
      <ToggleLed />
      <button onClick={togglePopup} className="toolbar-button">Edit</button>
      <Popup isOpen={isPopupOpen} />
    </div>
  );
};

export default Toolbar;