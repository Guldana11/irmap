package models

type Threat struct {
	ID       uint   `gorm:"primaryKey" json:"id"`
	Name     string `json:"name"`
	Category string `json:"category"`
	Severity string `json:"severity"`
	AssetID  uint   `json:"asset_id"` // связь с активом
}
