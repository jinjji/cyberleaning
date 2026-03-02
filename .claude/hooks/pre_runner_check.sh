#!/bin/bash
# Pre Hook: runner.py 실행 전 환경 검증

# 입력 JSON에서 명령어 추출
COMMAND=$(cat | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    cmd = data.get('tool_input', {}).get('command', '')
    print(cmd)
except:
    pass
")

# runner.py 실행이 아니면 그대로 종료
if ! echo "$COMMAND" | grep -qE "(python|python3).*runner\.py"; then
    exit 0
fi

# 프로젝트 루트
PROJECT_ROOT="/Users/jinhyeok/coding/test"
cd "$PROJECT_ROOT" || exit 0

# 에러 플래그
HAS_ERROR=0
HAS_WARNING=0

# 색상 정의
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔍 runner.py 실행 전 환경 검증"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 1. 필수 템플릿 4개 확인
REQUIRED_TEMPLATES=("IMG_POPUP1.png" "IMG_POPUP2.png" "IMG_EXIT.png" "IMG_START.png")
for template in "${REQUIRED_TEMPLATES[@]}"; do
    if [ ! -f "assets/$template" ]; then
        echo -e "${RED}❌ 필수 템플릿 누락: assets/$template${NC}"
        HAS_ERROR=1
    else
        echo -e "${GREEN}✅ 필수 템플릿 OK: assets/$template${NC}"
    fi
done

# 2. IMG_PLAYER.png (선택 항목, 없으면 warning)
if [ ! -f "assets/IMG_PLAYER.png" ]; then
    echo -e "${YELLOW}⚠️  선택 템플릿 누락: assets/IMG_PLAYER.png (fallback 사용됨)${NC}"
    HAS_WARNING=1
else
    echo -e "${GREEN}✅ 선택 템플릿 OK: assets/IMG_PLAYER.png${NC}"
fi

# 3. .venv 확인
if [ ! -d ".venv" ]; then
    echo -e "${RED}❌ 가상 환경 없음: .venv/ 디렉토리가 없습니다${NC}"
    echo "   명령어: python3 -m venv .venv"
    HAS_ERROR=1
else
    echo -e "${GREEN}✅ 가상 환경 OK: .venv/${NC}"
fi


echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 결과 판정
if [ $HAS_ERROR -eq 1 ]; then
    echo -e "${RED}🛑 검증 실패: 위의 오류를 수정한 후 다시 실행하세요${NC}"
    exit 2
elif [ $HAS_WARNING -eq 1 ]; then
    echo -e "${YELLOW}⚠️  경고 있음: 실행은 진행되지만 일부 기능이 제한될 수 있습니다${NC}"
    exit 0
else
    echo -e "${GREEN}✅ 모든 검증 통과! runner.py를 실행합니다${NC}"
    exit 0
fi
