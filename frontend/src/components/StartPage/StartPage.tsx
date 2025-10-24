import React from "react";
import "./StartPage.css";

const StartPage: React.FC = () => {
  const [range, setRange] = React.useState("month");
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

  return (
    <div className="startpage-container">
      <div className="startpage-box">
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
        </form>
      </div>
    </div>
  );
};

export default StartPage;
