import { useQuery } from "@tanstack/react-query";
import axios from "axios";
import type { DashboardSnapshot, EntitySignal, ValidationMetrics, KeywordNode } from "../types";

const api = axios.create({ baseURL: "/api" });

export function useDashboard(windowHours = 6) {
  return useQuery<DashboardSnapshot>({
    queryKey: ["dashboard", windowHours],
    queryFn: () => api.get(`/dashboard?window_hours=${windowHours}`).then(r => r.data),
  });
}

export function useSignals(windowHours = 6, sector?: string) {
  return useQuery<EntitySignal[]>({
    queryKey: ["signals", windowHours, sector],
    queryFn: () =>
      api
        .get(`/signals?window_hours=${windowHours}${sector ? `&sector=${sector}` : ""}`)
        .then(r => r.data),
  });
}

export function useValidation(windowHours = 6) {
  return useQuery<ValidationMetrics>({
    queryKey: ["validation", windowHours],
    queryFn: () => api.get(`/validation?window_hours=${windowHours}`).then(r => r.data),
  });
}

export function useKeywords(windowHours = 6) {
  return useQuery<KeywordNode[]>({
    queryKey: ["keywords", windowHours],
    queryFn: () => api.get(`/keywords?window_hours=${windowHours}&limit=100`).then(r => r.data),
  });
}
