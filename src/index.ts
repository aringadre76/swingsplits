import { serve } from "bun";
import index from "./index.html";

const server = serve({
  routes: {
    "/data/hitter_aggregates.json": {
      async GET() {
        return new Response(Bun.file("data/hitter_aggregates.json"));
      },
    },
    "/data/meta.json": {
      async GET() {
        return new Response(Bun.file("data/meta.json"));
      },
    },
    "/*": index,
    "/api/hello": {
      async GET(req) {
        return Response.json({
          message: "Hello, world!",
          method: "GET",
        });
      },
      async PUT(req) {
        return Response.json({
          message: "Hello, world!",
          method: "PUT",
        });
      },
    },

    "/api/hello/:name": async req => {
      const name = req.params.name;
      return Response.json({
        message: `Hello, ${name}!`,
      });
    },
  },

  development: process.env.NODE_ENV !== "production" && {
    hmr: true,
    console: true,
  },
});

console.log(`Server running at ${server.url}`);
