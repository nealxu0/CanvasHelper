import React from "react";
import "./ChatDisplay.css";

const WELCOME_TEXT = "Welcome! Ask me anything about your Canvas courses.";

interface ChatDisplayProps {
  onWelcomeDone?: () => void;
  messages: { role: "ai" | "user"; text: string }[];
}

const ChatDisplay: React.FC<ChatDisplayProps> = ({
  onWelcomeDone,
  messages,
}) => {
  // Typewriter for first AI message only
  const [typed, setTyped] = React.useState("");
  React.useEffect(() => {
    if (!messages.length || messages[0].role !== "ai") return;
    let i = 0;
    let timeout: number;
    function typeNext() {
      if (i <= messages[0].text.length) {
        setTyped(messages[0].text.slice(0, i));
        i++;
        timeout = setTimeout(typeNext, 28);
      } else if (onWelcomeDone) {
        setTimeout(onWelcomeDone, 400);
      }
    }
    typeNext();
    return () => clearTimeout(timeout);
    // eslint-disable-next-line
  }, [messages, onWelcomeDone]);

  return (
    <div className="chatdisplay-container">
      {messages.map((msg, idx) =>
        msg.role === "ai" && idx === 0 ? (
          <div key={idx} className="chatdisplay-message chatdisplay-message-ai">
            {typed}
          </div>
        ) : msg.role === "ai" ? (
          <div key={idx} className="chatdisplay-message chatdisplay-message-ai">
            {msg.text}
          </div>
        ) : (
          <div
            key={idx}
            className="chatdisplay-message chatdisplay-message-user"
          >
            {msg.text}
          </div>
        )
      )}
    </div>
  );
};

export default ChatDisplay;
