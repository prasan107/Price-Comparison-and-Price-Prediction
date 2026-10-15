import axios from "axios";

const api = axios.create({
  baseURL: "/api",
  timeout: 90000,   // scraping can take up to 60s — generous timeout
});

export const searchProducts  = (query)      => api.post("/search",           { query });
export const getProduct      = (id)         => api.get(`/products/${id}`);
export const getPrediction   = (id)         => api.get(`/predict/${id}`);
export const getPriceHistory = (id)         => api.get(`/history/${id}`);
export const createAlert     = (payload)    => api.post("/alerts",            payload);
export const getAlerts       = (email)      => api.get("/alerts",            { params: { email } });
export const deleteAlert     = (alertId)    => api.delete(`/alerts/${alertId}`);

export default api;
