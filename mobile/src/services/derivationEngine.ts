// derivationEngine.ts
// Calculates missing subjective scores from physical metrics.

export const deriveStressLevel = (heartRate: number, sleepHours: number): number => {
  // Base stress starts at 4 (neutral-mild)
  let stress = 4;

  // Heart rate contribution — clinically, resting HR is the primary stress signal
  // Normal resting HR: 60-80 bpm
  if (heartRate > 100) stress += 3;       // tachycardia — significant stress
  else if (heartRate > 90) stress += 2;   // elevated
  else if (heartRate > 80) stress += 1;   // mildly elevated
  else if (heartRate < 60) stress -= 1;   // athletic / relaxed

  // Sleep contribution
  // CRITICAL: 0h means HealthKit has no sleep data recorded (daytime query)
  // Do NOT penalize for 0h sleep — treat as "unknown", not "no sleep"
  if (sleepHours === 0) {
    // No adjustment — daytime reading, sleep not yet recorded
  } else if (sleepHours < 5) {
    stress += 3;   // severe deprivation
  } else if (sleepHours < 6.5) {
    stress += 1.5; // mild deprivation
  } else if (sleepHours >= 7.5) {
    stress -= 1;   // well-rested
  }

  return Math.max(1, Math.min(10, Math.round(stress))); // Clamp 1-10
};

export const deriveDietScore = (bmi: number, steps: number): number => {
  // Base diet score
  let diet = 6;

  // Activity level is a loose proxy for dietary awareness
  if (steps > 12000) diet += 2;
  else if (steps > 8000) diet += 1;
  else if (steps < 3000) diet -= 2;

  // BMI in healthy range suggests nutritional stability
  if (bmi >= 18.5 && bmi <= 25) diet += 1;
  else if (bmi > 30 || bmi < 17) diet -= 1;

  return Math.max(1, Math.min(10, Math.round(diet))); // Clamp 1-10
};
