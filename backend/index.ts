import express from "express";
import cors from "cors";
import { setupApp } from "./src/setup";
import { sequelize } from "./src/db";
import dotenv from "dotenv";
import companyRoutes from "./src/routes/company.routes";
dotenv.config();

const app = express();
const PORT = process.env.PORT || 3001;

setupApp(app);

app.use("/api/company", companyRoutes);

sequelize.sync({ force: false }).then(() => {
  console.log("DB synced");
  app.listen(PORT, () => {
    console.log(`Server running on port ${PORT}`);
  });
});
