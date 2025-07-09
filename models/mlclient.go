package models

import (
	"bytes"
	"encoding/json"
	"net/http"
)

type MLResponse struct {
	Asset          string  `json:"asset"`
	RiskLevel      string  `json:"risk_level"`
	RiskScore      float64 `json:"risk_score"`
	Recommendation string  `json:"recommendation"`
}

func AnalyzeRisk(asset Asset) (map[string]interface{}, error) {
	// Преобразуем структуру в JSON
	jsonData, err := json.Marshal(asset)
	if err != nil {
		return nil, err
	}

	// Отправляем POST-запрос
	resp, err := http.Post("http://127.0.0.1:5000/analyze", "application/json", bytes.NewBuffer(jsonData))
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	// Читаем и парсим ответ
	var result map[string]interface{}
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, err
	}

	return result, nil
}
