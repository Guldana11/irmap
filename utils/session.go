package utils

var sessions = map[string]string{
	// Пример: session_token => username
	"abc123": "admin",
}

// Проверка валидности сессии
func IsValidSession(token string) bool {
	_, exists := sessions[token]
	return exists
}

// Получение имени пользователя из токена
func GetUserFromSession(token string) (string, bool) {
	user, exists := sessions[token]
	return user, exists
}

// Добавление новой сессии
func CreateSession(token, username string) {
	sessions[token] = username
}

// Удаление сессии
func DeleteSession(token string) {
	delete(sessions, token)
}
