import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';

/**
 * Typewriter — Animated typing effect with delete + loop.
 * Adapted from TSX/Tailwind to plain JS/inline styles for CRA.
 *
 * Props:
 *   text: string | string[] — text(s) to type
 *   speed: number — typing speed in ms (default 50)
 *   initialDelay: number — delay before first character (default 0)
 *   waitTime: number — pause after full text before deleting (default 2000)
 *   deleteSpeed: number — delete speed in ms (default 30)
 *   loop: boolean — loop through texts (default true)
 *   className: string — optional CSS class
 *   style: object — optional inline styles for the text
 *   showCursor: boolean — show blinking cursor (default true)
 *   hideCursorOnType: boolean — hide cursor while typing (default false)
 *   cursorChar: string — cursor character (default '|')
 *   cursorStyle: object — inline styles for cursor
 */
export function Typewriter({
  text,
  speed = 50,
  initialDelay = 0,
  waitTime = 2000,
  deleteSpeed = 30,
  loop = true,
  className,
  style = {},
  showCursor = true,
  hideCursorOnType = false,
  cursorChar = '|',
  cursorStyle = {},
}) {
  const [displayText, setDisplayText] = useState('');
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isDeleting, setIsDeleting] = useState(false);
  const [currentTextIndex, setCurrentTextIndex] = useState(0);

  const texts = Array.isArray(text) ? text : [text];

  useEffect(() => {
    let timeout;
    const currentText = texts[currentTextIndex];

    const startTyping = () => {
      if (isDeleting) {
        if (displayText === '') {
          setIsDeleting(false);
          if (currentTextIndex === texts.length - 1 && !loop) return;
          setCurrentTextIndex((prev) => (prev + 1) % texts.length);
          setCurrentIndex(0);
          timeout = setTimeout(() => {}, waitTime);
        } else {
          timeout = setTimeout(() => {
            setDisplayText((prev) => prev.slice(0, -1));
          }, deleteSpeed);
        }
      } else {
        if (currentIndex < currentText.length) {
          timeout = setTimeout(() => {
            setDisplayText((prev) => prev + currentText[currentIndex]);
            setCurrentIndex((prev) => prev + 1);
          }, speed);
        } else if (texts.length > 1) {
          timeout = setTimeout(() => {
            setIsDeleting(true);
          }, waitTime);
        }
      }
    };

    if (currentIndex === 0 && !isDeleting && displayText === '') {
      timeout = setTimeout(startTyping, initialDelay);
    } else {
      startTyping();
    }

    return () => clearTimeout(timeout);
  }, [currentIndex, displayText, isDeleting, speed, deleteSpeed, waitTime, texts, currentTextIndex, loop, initialDelay]);

  const shouldHideCursor =
    hideCursorOnType &&
    (currentIndex < texts[currentTextIndex].length || isDeleting);

  return (
    <span
      className={className}
      style={{ display: 'inline', whiteSpace: 'pre-wrap', letterSpacing: '-.02em', ...style }}
    >
      <span>{displayText}</span>
      {showCursor && (
        <motion.span
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.01, repeat: Infinity, repeatDelay: 0.4, repeatType: 'reverse' }}
          style={{
            marginLeft: 2,
            display: shouldHideCursor ? 'none' : 'inline',
            ...cursorStyle,
          }}
        >
          {cursorChar}
        </motion.span>
      )}
    </span>
  );
}
