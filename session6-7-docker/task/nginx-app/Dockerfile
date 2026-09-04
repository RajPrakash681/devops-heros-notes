FROM nginx:alpine

# Replace the default welcome page with our own. No build step - nginx already
# knows how to serve a directory, so the image is just base + one file.
COPY index.html /usr/share/nginx/html/index.html

EXPOSE 80
