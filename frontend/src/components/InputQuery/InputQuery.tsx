import React, { useRef } from "react";
import "./InputQuery.css";

interface InputQueryProps {
  reappear?: boolean;
  onSend?: (text: string) => void;
}

const InputQuery: React.FC<InputQueryProps> = ({ reappear, onSend }) => {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const maxHeight = 180;
  const [value, setValue] = React.useState("");
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
  return (
    <div className="inputquery-container">
      <div
        className={`inputquery-textarea-wrapper${
          reappear ? " inputquery-reappear" : ""
        }`}
      >
        <textarea
          ref={textareaRef}
          className="inputquery-box"
          placeholder="Type your question or follow-up..."
          rows={1}
          style={{ resize: "none" }}
          value={value}
          onInput={handleInput}
          onKeyDown={handleKeyDown}
        />
        <button className="inputquery-send" type="button" onClick={handleSend}>
          ↑
        </button>
      </div>
    </div>
  );
};

export default InputQuery;
