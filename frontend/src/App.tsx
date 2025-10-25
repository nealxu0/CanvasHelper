import React from "react";
import Title from "./components/Title/Title";
import StartPage from "./components/StartPage/StartPage";
import InputQuery from "./components/InputQuery/InputQuery";
import ChatDisplay from "./components/ChatDisplay/ChatDisplay";
import "./App.css";

function App() {
  const [showMain, setShowMain] = React.useState(false);
  const [showInput, setShowInput] = React.useState(false);
  const [messages, setMessages] = React.useState<
    { role: "ai" | "user"; text: string }[]
  >([]);

  // Show input after welcome message is done
  const handleWelcomeDone = React.useCallback(() => {
    setShowInput(true);
  }, []);

  // Add welcome message on showMain
  React.useEffect(() => {
    if (showMain) {
      setMessages([
        {
          role: "ai",
          text: "Welcome! Ask me anything about your Canvas courses.",
        },
      ]);
    }
  }, [showMain]);

  const handleSend = (text: string) => {
    if (text.trim()) {
      setMessages((prev) => [...prev, { role: "user", text }]);
    }
  };

  return (
    <div>
      <Title />
      {!showMain && <StartPage onFinish={() => setShowMain(true)} />}
      {showMain && (
        <>
          <ChatDisplay onWelcomeDone={handleWelcomeDone} messages={messages} />
          {showInput && <InputQuery reappear onSend={handleSend} />}
        </>
      )}
    </div>
  );
}

export default App;
