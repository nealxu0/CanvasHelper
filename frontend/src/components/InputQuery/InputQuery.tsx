import React, { useRef } from "react";
import { FaArrowUp } from "react-icons/fa";
import "./InputQuery.css";

interface InputQueryProps {
  reappear?: boolean;
}

const InputQuery: React.FC<InputQueryProps> = ({ reappear }) => {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const maxHeight = 180;
  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const ta = textareaRef.current;
    if (ta) {
      ta.style.height = "auto";
      ta.style.height = Math.min(ta.scrollHeight, maxHeight) + "px";
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
          onInput={handleInput}
        />
        <button className="inputquery-send" type="button">
          <FaArrowUp size={18} />
        </button>
      </div>
    </div>
  );
};

export default InputQuery;
