import React, { useRef, useState, useEffect } from "react";
import "./InputQuery.css";

interface InputQueryProps {
  reappear?: boolean;
  onSend?: (text: string) => void;
}

const InputQuery: React.FC<InputQueryProps> = ({ reappear, onSend }) => {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const recognitionRef = useRef<any>(null);
  const maxHeight = 180;
  const [value, setValue] = useState("");
  const [isListening, setIsListening] = useState(false);
  const [isSupported, setIsSupported] = useState(false);
  const [showMic, setShowMic] = useState(false);

  useEffect(() => {
    if (reappear) {
      const timer = setTimeout(() => setShowMic(true), 800);
      return () => clearTimeout(timer);
    } else {
      setShowMic(true);
    }
  }, [reappear]);

  useEffect(() => {
    const SpeechRecognition =
      (window as any).SpeechRecognition ||
      (window as any).webkitSpeechRecognition;
    if (SpeechRecognition) {
      setIsSupported(true);
      recognitionRef.current = new SpeechRecognition();
      recognitionRef.current.continuous = true;
      recognitionRef.current.interimResults = true;
      recognitionRef.current.lang = "en-US";

      recognitionRef.current.onresult = (event: any) => {
        let transcript = "";
        for (let i = event.resultIndex; i < event.results.length; i++) {
          transcript += event.results[i][0].transcript;
        }
        setValue(transcript);
        if (textareaRef.current) {
          textareaRef.current.style.height = "auto";
          textareaRef.current.style.height =
            Math.min(textareaRef.current.scrollHeight, maxHeight) + "px";
        }
      };

      recognitionRef.current.onerror = (event: any) => {
        console.error("Speech recognition error:", event.error);
        setIsListening(false);
      };
    }
    // Cleanup
    return () => {
      if (recognitionRef.current) recognitionRef.current.stop();
    };
  }, []);

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const ta = textareaRef.current;
    setValue(e.target.value);
    if (ta) {
      ta.style.height = "auto";
      ta.style.height = Math.min(ta.scrollHeight, maxHeight) + "px";
    }
  };

  const handleSend = () => {
    if (onSend && value.trim()) {
      onSend(value);
      setValue("");
      if (textareaRef.current) {
        textareaRef.current.style.height = "48px";
      }
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const toggleListening = () => {
    if (!isSupported) {
      alert(
        "Speech recognition is not supported in your browser. Please use Chrome, Safari, or Edge."
      );
      return;
    }
    if (isListening) {
      recognitionRef.current?.stop();
      setIsListening(false);
    } else {
      setValue("");
      recognitionRef.current?.start();
      setIsListening(true);
    }
  };

  return (
    <div className="inputquery-container">
      <div
        className={`inputquery-textarea-wrapper${
          reappear ? " inputquery-reappear" : ""
        }`}
      >
        <textarea
          ref={textareaRef}
          className={`inputquery-box${
            isListening ? " inputquery-box-disabled" : ""
          }`}
          placeholder={
            isListening ? "Listening..." : "Type your question or follow-up..."
          }
          rows={1}
          style={{ resize: "none" }}
          value={value}
          onInput={handleInput}
          onKeyDown={handleKeyDown}
          disabled={isListening}
        />
        <button
          className="inputquery-send"
          type="button"
          onClick={handleSend}
          disabled={isListening}
        >
          ↑
        </button>
      </div>
      {showMic && (
        <button
          className={`inputquery-mic${
            isListening ? " inputquery-mic-active" : ""
          }`}
          type="button"
          onClick={toggleListening}
          title={isListening ? "Stop recording" : "Start voice input"}
          style={{
            width: "3rem",
            height: "3rem",
            padding: 0,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          {isListening ? (
            <svg
              width="70%"
              height="70%"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              style={{ display: "block" }}
            >
              <line x1="1" y1="1" x2="23" y2="23" />
              <path d="M9 9v3a3 3 0 0 0 5.12 2.12M15 9.34V4a3 3 0 0 0-5.94-.6" />
              <path d="M17 16.95A7 7 0 0 1 5 12v-2m14 0v2a7 7 0 0 1-.11 1.23" />
              <line x1="12" y1="19" x2="12" y2="23" />
              <line x1="8" y1="23" x2="16" y2="23" />
            </svg>
          ) : (
            <svg
              width="70%"
              height="70%"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              style={{ display: "block" }}
            >
              <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
              <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
              <line x1="12" y1="19" x2="12" y2="23" />
              <line x1="8" y1="23" x2="16" y2="23" />
            </svg>
          )}
        </button>
      )}
    </div>
  );
};

export default InputQuery;
