import Title from "./components/Title/Title";
import StartPage from "./components/StartPage/StartPage";
import InputQuery from "./components/InputQuery/InputQuery";
import ChatDisplay from "./components/ChatDisplay/ChatDisplay";
import React from "react";
import "./App.css";

function App() {
  const [showMain, setShowMain] = React.useState(false);
  const [showInput, setShowInput] = React.useState(false);

  // Show input after welcome message is done
  const handleWelcomeDone = React.useCallback(() => {
    setShowInput(true);
  }, []);

  return (
    <div>
      <Title />
      {!showMain && <StartPage onFinish={() => setShowMain(true)} />}
      {showMain && (
        <>
          <ChatDisplay onWelcomeDone={handleWelcomeDone} />
          {showInput && <InputQuery reappear />}
        </>
      )}
    </div>
  );
}

export default App;
