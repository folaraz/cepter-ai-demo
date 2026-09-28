// Railway Infrastructure as Code for the `app` service (replaces railway.json, whose
// Config as Code Railway no longer reads). Preview with `railway config plan`, apply with
// `railway config apply`; see backend/README.md "Deploy (Railway)".
//
// A named partial: this file owns only the app service. The Postgres service and its
// volume stay as configured in Railway, so nothing here can delete them.
import { defineRailway, preserve, project, service } from "railway/iac";

export const partial = "app";

export default defineRailway(() => {
  const app = service("app", {
    // No source: the app is uploaded with `railway up` until Railway's GitHub app can
    // see the repository.
    build: {
      builder: "DOCKERFILE",
      dockerfilePath: "Dockerfile",
    },
    deploy: {
      preDeployCommand: ["lens release"],
      healthcheckPath: "/api/health",
      healthcheckTimeout: 120,
      restartPolicyType: "ON_FAILURE",
    },
    env: {
      // Built from the postgres service's variables in Railway; kept as set there.
      DATABASE_URL: preserve(),
      COOKIE_SECURE: "true",
      LLM_MODE: "replay",
      ASK_LIVE: "false",
      // Belt and braces with `builder` above: without it Railway fell back to Railpack
      // and failed with "No start command detected".
      RAILWAY_DOCKERFILE_PATH: "Dockerfile",
    },
  });

  return project("gracious-acceptance", {
    resources: [app],
  });
});
