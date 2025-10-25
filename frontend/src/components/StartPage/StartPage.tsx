import React, { useRef } from "react";
import "./StartPage.css";

interface StartPageProps {
  onFinish?: () => void;
}

const StartPage: React.FC<StartPageProps> = ({ onFinish }) => {
  const [range, setRange] = React.useState("");
  const [hidden, setHidden] = React.useState(false);
  const [disappearing, setDisappearing] = React.useState(false);
  const boxRef = useRef<HTMLDivElement>(null);
  const [customStart, setCustomStart] = React.useState("");
  const [customEnd, setCustomEnd] = React.useState("");

  // Typewriter effect logic
  const phrases = ["exams", "homework", "assignments", "projects", "school"];
  const [currentPhrase, setCurrentPhrase] = React.useState(0);
  const [displayText, setDisplayText] = React.useState("");
  const [deleting, setDeleting] = React.useState(false);

  React.useEffect(() => {
    let timeout: ReturnType<typeof setTimeout>;
    const fullText = `Let's ace our ${phrases[currentPhrase]}.`;
    const staticLength = `Let's ace our `.length;
    if (!deleting && displayText.length < fullText.length) {
      timeout = setTimeout(() => {
        setDisplayText(fullText.slice(0, displayText.length + 1));
      }, 110);
    } else if (deleting && displayText.length > staticLength) {
      timeout = setTimeout(() => {
        setDisplayText(fullText.slice(0, displayText.length - 1));
      }, 65);
    } else if (!deleting && displayText.length === fullText.length) {
      timeout = setTimeout(() => setDeleting(true), 1100);
    } else if (deleting && displayText.length === staticLength) {
      timeout = setTimeout(() => {
        setDeleting(false);
        setCurrentPhrase((prev) => (prev + 1) % phrases.length);
      }, 500);
    }
    return () => clearTimeout(timeout);
  }, [displayText, deleting, currentPhrase, phrases]);

  // Prompt options logic
  const promptOptions = [
    { label: "Summarize these", value: "summarize" },
    { label: "What is this assignment on?", value: "what" },
    { label: "Suggest study plan", value: "plan" },
    { label: "Custom", value: "custom" },
  ];
  const [selectedPrompt, setSelectedPrompt] = React.useState<string | null>(
    null
  );
  const [customPrompt, setCustomPrompt] = React.useState("");

  // Button enable logic
  const isDateValid =
    (range === "custom" ? customStart && customEnd : !!range) && range !== "";
  const isPromptValid =
    selectedPrompt &&
    (selectedPrompt !== "custom" ||
      (selectedPrompt === "custom" && customPrompt.trim() !== ""));
  const canStart = isDateValid && isPromptValid;

  if (hidden) return null;

  const handleDisappear = () => {
    setDisappearing(true);
    setTimeout(() => {
      setHidden(true);
      if (onFinish) onFinish();
    }, 700); // match animation duration
  };

  return (
    <div className="startpage-container">
      <div
        className={`startpage-box${
          disappearing ? " startpage-box-disappear" : ""
        }`}
        ref={boxRef}
      >
        <form className="startpage-form">
          <div className="startpage-typewriter">
            {displayText}
            <span className="startpage-cursor">|</span>
          </div>
          <label htmlFor="range-select" className="startpage-label">
            Summarize for:
          </label>
          <div className="startpage-select-wrapper">
            <select
              id="range-select"
              className="startpage-select"
              value={range}
              onChange={(e) => setRange(e.target.value)}
            >
              <option value="" disabled hidden>
                Choose an option
              </option>
              <option value="month">This Month</option>
              <option value="week">This Week</option>
              <option value="today">Today</option>
              <option value="custom">Custom Range</option>
            </select>
          </div>

          {range === "custom" && (
            <div className="startpage-custom-range">
              <input
                type="date"
                value={customStart}
                onChange={(e) => setCustomStart(e.target.value)}
                className="startpage-date"
                placeholder="Start date"
              />
              <span style={{ margin: "0 0.5rem" }}>to</span>
              <input
                type="date"
                value={customEnd}
                onChange={(e) => setCustomEnd(e.target.value)}
                className="startpage-date"
                placeholder="End date"
              />
            </div>
          )}

          {/* Prompt options buttons */}
          <div className="startpage-prompt-options">
            {promptOptions.map((opt) => (
              <button
                type="button"
                key={opt.value}
                onClick={() => setSelectedPrompt(opt.value)}
                className={`startpage-prompt-btn${
                  selectedPrompt === opt.value ? " selected" : ""
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>

          {/* Show custom input if custom is selected */}
          {selectedPrompt === "custom" && (
            <div
              className={`startpage-custom-input${
                range === "custom" ? " both-custom-active" : ""
              }`}
            >
              <input
                type="text"
                value={customPrompt}
                onChange={(e) => setCustomPrompt(e.target.value)}
                placeholder="Type your custom prompt..."
                className="startpage-custom-input-field"
              />
            </div>
          )}

          {/* Start Summarizing button */}
          <button
            type="button"
            className={`startpage-submit-btn${canStart ? " enabled" : ""}`}
            disabled={!canStart}
            onClick={handleDisappear}
          >
            <span>Start Summarizing</span>
          </button>
        </form>
      </div>
    </div>
  );
};

export default StartPage;
