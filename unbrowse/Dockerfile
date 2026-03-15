FROM node:22-slim

RUN npm install -g unbrowse

ENV HOST=0.0.0.0
ENV PORT=6969
EXPOSE 6969

# Accept ToS and start server
CMD echo "y" | unbrowse setup --skip-browser
