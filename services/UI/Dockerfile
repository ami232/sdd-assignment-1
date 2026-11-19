# syntax=docker/dockerfile:1
# The UI is plain HTML, CSS and JavaScript, so it needs no build step and
# no Python: nginx serves the files and forwards API calls to the services.
# The unprivileged image runs nginx as a non-root user, like the other images.
FROM nginxinc/nginx-unprivileged:1.27-alpine

# Where the two services live. Compose uses their service names; in the
# cloud these are set to the services' real URLs.
ENV PORT=8080 \
    TRIPS_URL=http://trip-management:8000 \
    ROOMS_URL=http://room-allocation:8000

# nginx fills in ${PORT}, ${TRIPS_URL} and ${ROOMS_URL} from the
# environment when the container starts.
COPY nginx.conf.template /etc/nginx/templates/default.conf.template
COPY site/ /usr/share/nginx/html/

EXPOSE 8080
