import AppleHealthKit, { HealthValue, HealthKitPermissions } from 'react-native-health';

const permissions: HealthKitPermissions = {
  permissions: {
    read: [
      AppleHealthKit.Constants.Permissions.HeartRate,
      AppleHealthKit.Constants.Permissions.RestingHeartRate,
      AppleHealthKit.Constants.Permissions.Steps,
      AppleHealthKit.Constants.Permissions.SleepAnalysis,
      AppleHealthKit.Constants.Permissions.BodyMassIndex,
      AppleHealthKit.Constants.Permissions.BodyMass,
      AppleHealthKit.Constants.Permissions.Height,
      AppleHealthKit.Constants.Permissions.OxygenSaturation,
      AppleHealthKit.Constants.Permissions.MindfulSession,
      AppleHealthKit.Constants.Permissions.Water,
      AppleHealthKit.Constants.Permissions.ActiveEnergyBurned,
      AppleHealthKit.Constants.Permissions.BloodPressureDiastolic,
      AppleHealthKit.Constants.Permissions.BloodPressureSystolic,
    ],
    write: [],
  },
};

export const initHealthKit = (): Promise<void> => {
  return new Promise((resolve, reject) => {
    AppleHealthKit.initHealthKit(permissions, (error: string) => {
      if (error) {
        console.error('[HealthKit Error]', error);
        reject(error);
      } else {
        resolve();
      }
    });
  });
};

export const fetchHealthDataSnapshot = async (): Promise<{
  heartRate: number;
  steps: number;
  sleep: number;
  bmi: number;
  weightKg: number | null;
  heightM: number | null;
}> => {
  return new Promise((resolve, reject) => {
    let heartRate = 72;
    let steps = 0;
    let sleep = 0.0;
    let bmi = 23.5;       // fallback only
    let weightKg: number | null = null;
    let heightM: number | null = null;

    const startOfToday = new Date();
    startOfToday.setHours(0, 0, 0, 0);

    const optionsToday = { startDate: startOfToday.toISOString() };
    const options24h = { startDate: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString() };
    const optionsLiveToday = { date: new Date().toISOString() };

    AppleHealthKit.getStepCount(optionsLiveToday, (err, result) => {
      if (!err && result && result.value) steps = result.value;

      AppleHealthKit.getHeartRateSamples(optionsToday, (err, results) => {
        if (!err && results && results.length > 0) {
          const sorted = results.sort((a, b) => new Date(b.endDate).getTime() - new Date(a.endDate).getTime());
          heartRate = sorted[0].value;
        }

        AppleHealthKit.getSleepSamples(options24h, (err, results) => {
          if (!err && results && results.length > 0) {
            const totalSleepMs = results.reduce((acc, curr) => {
              const start = new Date(curr.startDate).getTime();
              const end = new Date(curr.endDate).getTime();
              return acc + (end - start);
            }, 0);
            sleep = totalSleepMs / (1000 * 60 * 60);
          }

          // Fetch weight in POUNDS (most reliable default in react-native-health)
          // then convert to kg manually — avoids unit mismatch bugs
          AppleHealthKit.getLatestWeight({ unit: 'pound' } as any, (errW, weightResult) => {
            AppleHealthKit.getLatestHeight({ unit: 'meter' } as any, (errH, heightResult) => {

              if (!errW && weightResult && weightResult.value > 0) {
                // Always treat the returned value as pounds and convert
                weightKg = weightResult.value * 0.453592;
              }

              if (!errH && heightResult && heightResult.value > 0) {
                // Sanity check: adult height must be between 1.2m and 2.5m
                // If value > 3 it's in cm → convert. If still out of range → discard.
                const rawH = heightResult.value;
                const candidateH = rawH > 3 ? rawH / 100 : rawH;
                if (candidateH >= 1.2 && candidateH <= 2.5) {
                  heightM = candidateH;
                }
              }

              if (weightKg && heightM && heightM > 0) {
                // BMI = weight(kg) / height(m)²
                const computed = weightKg / (heightM * heightM);
                // Sanity check: valid human BMI is 10–60. Discard if outside range.
                if (computed >= 10 && computed <= 60) {
                  bmi = computed;
                } else {
                  // Bad unit combo — fall back to HealthKit stored value
                  AppleHealthKit.getLatestBmi(null as any, (errB, bmiResult) => {
                    if (!errB && bmiResult && bmiResult.value) bmi = bmiResult.value;
                  });
                } // closes else
              } // closes if (weightKg && heightM)

              resolve({
                heartRate: Math.round(heartRate),
                steps: Math.round(steps),
                sleep: Number(sleep.toFixed(1)),
                bmi: Number(bmi.toFixed(1)),
                weightKg: weightKg ? Number(weightKg.toFixed(1)) : null,
                heightM: heightM ? Number(heightM.toFixed(2)) : null,
              });
            });
          });
        });
      });
    });
  });
};
