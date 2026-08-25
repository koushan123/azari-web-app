@echo off
call npm.cmd run typecheck || exit /b 1
call npm.cmd exec vite -- build --ssr tests/frontend.test.tsx --outDir .test-dist || exit /b 1
node --test .test-dist/frontend.test.js
