import { Express } from "express";
import express from "express";
import cors from "cors";
import companyRoutes from "./routes/company.routes";

export const setupApp = (app: Express) => {
  app.use(cors());
  app.use(express.json());
  app.use(express.urlencoded({ extended: false }));

  app.get("/api/health", (_req, res) => {
    res.send({ status: "ok" });
  });

  app.use("/api/companies", companyRoutes);
};
