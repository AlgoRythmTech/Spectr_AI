import React, { memo } from 'react';
import { AnimatePresence, motion } from 'framer-motion';

/**
 * Text Effect — animated text reveal with presets (blur, shake, scale, fade, slide).
 * Adapted from TypeScript/Tailwind to plain JS/inline styles for CRA.
 *
 * Props:
 *   children: string — the text to animate
 *   per: 'word' | 'char' | 'line' — split method
 *   as: string — HTML tag (e.g., 'h1', 'p', 'span')
 *   preset: 'blur' | 'shake' | 'scale' | 'fade' | 'slide'
 *   delay: number — delay before animation starts
 *   trigger: boolean — mount/unmount control
 *   className: string — optional CSS class
 *   style: object — optional inline style
 *   variants: { container, item } — custom framer-motion variants
 *   onAnimationComplete: function
 */

const defaultStaggerTimes = { char: 0.03, word: 0.05, line: 0.1 };

const defaultContainerVariants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { staggerChildren: 0.05 } },
  exit: { transition: { staggerChildren: 0.05, staggerDirection: -1 } },
};

const defaultItemVariants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1 },
  exit: { opacity: 0 },
};

const presetVariants = {
  blur: {
    container: defaultContainerVariants,
    item: {
      hidden: { opacity: 0, filter: 'blur(12px)' },
      visible: { opacity: 1, filter: 'blur(0px)' },
      exit: { opacity: 0, filter: 'blur(12px)' },
    },
  },
  shake: {
    container: defaultContainerVariants,
    item: {
      hidden: { x: 0 },
      visible: { x: [-5, 5, -5, 5, 0], transition: { duration: 0.5 } },
      exit: { x: 0 },
    },
  },
  scale: {
    container: defaultContainerVariants,
    item: {
      hidden: { opacity: 0, scale: 0 },
      visible: { opacity: 1, scale: 1 },
      exit: { opacity: 0, scale: 0 },
    },
  },
  fade: {
    container: defaultContainerVariants,
    item: {
      hidden: { opacity: 0 },
      visible: { opacity: 1 },
      exit: { opacity: 0 },
    },
  },
  slide: {
    container: defaultContainerVariants,
    item: {
      hidden: { opacity: 0, y: 20 },
      visible: { opacity: 1, y: 0 },
      exit: { opacity: 0, y: 20 },
    },
  },
};

const AnimationComponent = memo(function AnimationComponent({ segment, variants, per }) {
  if (per === 'line') {
    return (
      <motion.span variants={variants} style={{ display: 'block' }}>
        {segment}
      </motion.span>
    );
  }

  if (per === 'word') {
    return (
      <motion.span
        aria-hidden="true"
        variants={variants}
        style={{ display: 'inline-block', whiteSpace: 'pre' }}
      >
        {segment}
      </motion.span>
    );
  }

  // per === 'char'
  return (
    <motion.span style={{ display: 'inline-block', whiteSpace: 'pre' }}>
      {segment.split('').map((char, i) => (
        <motion.span
          key={`char-${i}`}
          aria-hidden="true"
          variants={variants}
          style={{ display: 'inline-block', whiteSpace: 'pre' }}
        >
          {char}
        </motion.span>
      ))}
    </motion.span>
  );
});

export function TextEffect({
  children,
  per = 'word',
  as = 'p',
  variants,
  className,
  style = {},
  preset,
  delay = 0,
  trigger = true,
  onAnimationComplete,
}) {
  let segments;
  if (per === 'line') {
    segments = children.split('\n');
  } else if (per === 'word') {
    segments = children.split(/(\s+)/);
  } else {
    segments = children.split('');
  }

  const MotionTag = motion[as] || motion.p;
  const selectedVariants = preset
    ? presetVariants[preset]
    : { container: defaultContainerVariants, item: defaultItemVariants };
  const containerVariants = variants?.container || selectedVariants.container;
  const itemVariants = variants?.item || selectedVariants.item;
  const stagger = defaultStaggerTimes[per];

  const delayedContainerVariants = {
    hidden: containerVariants.hidden,
    visible: {
      ...containerVariants.visible,
      transition: {
        ...(containerVariants.visible?.transition || {}),
        staggerChildren: containerVariants.visible?.transition?.staggerChildren || stagger,
        delayChildren: delay,
      },
    },
    exit: containerVariants.exit,
  };

  return (
    <AnimatePresence mode="popLayout">
      {trigger && (
        <MotionTag
          initial="hidden"
          animate="visible"
          exit="exit"
          variants={delayedContainerVariants}
          className={className}
          style={{ whiteSpace: 'pre-wrap', ...style }}
          onAnimationComplete={onAnimationComplete}
        >
          {segments.map((segment, index) => (
            <AnimationComponent
              key={`${per}-${index}-${segment}`}
              segment={segment}
              variants={itemVariants}
              per={per}
            />
          ))}
        </MotionTag>
      )}
    </AnimatePresence>
  );
}
