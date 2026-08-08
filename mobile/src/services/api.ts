import axios from 'axios';

// Connectng to the ngrok tunnel created for DarpanAI backend
export const API_BASE_URL = 'https://7272-103-97-164-99.ngrok-free.app';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export interface HealthDataInput {
  user_id: string;
  heart_rate: number;
  sleep: number;
  steps: number;
  stress_level: number;
  diet_score: number;
  bmi: number;
}

export const submitHealthData = async (data: HealthDataInput) => {
  const response = await apiClient.post('/health-data', data);
  return response.data;
};

export const fetchRiskScore = async (userId: string) => {
  const response = await apiClient.get('/risk', { params: { user_id: userId } });
  return response.data;
};

export const fetchRiskHistory = async (userId: string) => {
  const response = await apiClient.get('/risk/history', { params: { user_id: userId } });
  return response.data;
};
