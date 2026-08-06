// apps/chat/page.tsx(대화 저장/복원)와 BottomNavBar(임시 초기화 더블클릭)가 같이 쓰는
// sessionStorage 키 — 페이지 컴포넌트를 서로 import하면 순환 참조가 생겨 별도 파일로 뺐다.
export const CHAT_MESSAGES_STORAGE_KEY = "inheritors-chat-messages";
export const CHAT_SESSION_ID_STORAGE_KEY = "inheritors-chat-session-id";
