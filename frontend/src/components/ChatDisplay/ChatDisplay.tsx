import React from "react";
import "./ChatDisplay.css";

const WELCOME_TEXT = "Welcome! Ask me anything about your Canvas courses.";

interface ChatDisplayProps {
  onWelcomeDone?: () => void;
}

const ChatDisplay: React.FC<ChatDisplayProps> = ({ onWelcomeDone }) => {
  const [typed, setTyped] = React.useState("");

  React.useEffect(() => {
    let i = 0;
    let timeout: number;
    function typeNext() {
      if (i <= WELCOME_TEXT.length) {
        setTyped(WELCOME_TEXT.slice(0, i));
        i++;
        timeout = setTimeout(typeNext, 28);
      } else if (onWelcomeDone) {
        setTimeout(onWelcomeDone, 400); // slight pause after typing
      }
    }
    typeNext();
    return () => clearTimeout(timeout);
    // eslint-disable-next-line
  }, []);

  return (
    <div className="chatdisplay-container">
      <div className="chatdisplay-message chatdisplay-message-ai">{typed}</div>
    </div>
  );
};

export default ChatDisplay;
