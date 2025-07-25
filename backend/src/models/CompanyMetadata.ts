import { DataTypes } from "sequelize";
import { sequelize } from "../db";

export const CompanyMetadata = sequelize.define("CompanyMetadata", {
  ticker: {
    type: DataTypes.STRING,
    primaryKey: true,
  },
  name: {
    type: DataTypes.STRING,
    allowNull: false,
  },
  ir_url: {
    type: DataTypes.STRING,
    allowNull: true,
  },
}, {
  timestamps: false
});
