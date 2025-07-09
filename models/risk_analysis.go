package models

import "time"

type RiskAnalysis struct {
	ID          uint `gorm:"primaryKey"`
	AssetID     uint
	RiskScore   float64
	Description string
	CreatedAt   time.Time
}
