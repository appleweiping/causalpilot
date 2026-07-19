"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { elapsedForPhase, phaseAtElapsed, STORY_DURATION_SECONDS } from "@/lib/story";

interface NarrativeOptions {
  onPhaseChange?: (phaseIndex: number) => void;
}

export function useNarrative({ onPhaseChange }: NarrativeOptions = {}) {
  const [phaseIndex, setPhaseIndex] = useState(0);
  const [elapsed, setElapsed] = useState(0);
  const [isRunning, setIsRunning] = useState(false);
  const originRef = useRef(0);
  const phaseRef = useRef(0);
  const onPhaseChangeRef = useRef(onPhaseChange);

  useEffect(() => {
    onPhaseChangeRef.current = onPhaseChange;
  }, [onPhaseChange]);

  const announcePhase = useCallback((next: number) => {
    if (phaseRef.current !== next) {
      phaseRef.current = next;
      setPhaseIndex(next);
      onPhaseChangeRef.current?.(next);
    }
  }, []);

  useEffect(() => {
    if (!isRunning) return;
    const timer = window.setInterval(() => {
      const nextElapsed = Math.min(
        STORY_DURATION_SECONDS,
        Math.max(0, (performance.now() - originRef.current) / 1000),
      );
      setElapsed(nextElapsed);
      announcePhase(phaseAtElapsed(nextElapsed));
      if (nextElapsed >= STORY_DURATION_SECONDS) setIsRunning(false);
    }, 100);
    return () => window.clearInterval(timer);
  }, [announcePhase, isRunning]);

  const start = useCallback(() => {
    phaseRef.current = 0;
    setPhaseIndex(0);
    setElapsed(0);
    originRef.current = performance.now();
    setIsRunning(true);
    onPhaseChangeRef.current?.(0);
  }, []);

  const jumpTo = useCallback((index: number, keepRunning = true, notify = true) => {
    const safeIndex = Math.max(0, Math.min(5, index));
    const nextElapsed = elapsedForPhase(safeIndex);
    phaseRef.current = safeIndex;
    setPhaseIndex(safeIndex);
    setElapsed(nextElapsed);
    originRef.current = performance.now() - nextElapsed * 1000;
    setIsRunning(keepRunning);
    if (notify) onPhaseChangeRef.current?.(safeIndex);
  }, []);

  const reset = useCallback(() => {
    phaseRef.current = 0;
    setPhaseIndex(0);
    setElapsed(0);
    setIsRunning(false);
  }, []);

  return {
    phaseIndex,
    elapsed,
    isRunning,
    progress: elapsed / STORY_DURATION_SECONDS,
    start,
    jumpTo,
    reset,
  };
}
