import { DataTypes } from "sequelize";
import { sequelize } from "../db";

export const Company = sequelize.define("Company", {
  name: {
    type: DataTypes.STRING,
    allowNull: false,
  },
  ticker: {
    type: DataTypes.STRING,
    allowNull: false,
  },
  year: {
    type: DataTypes.INTEGER,
    allowNull: false,
  },
  statement_type: {
    type: DataTypes.STRING,
    allowNull: false,
  },
  metric: {
    type: DataTypes.STRING,
    allowNull: false,
  },
  value: {
    type: DataTypes.FLOAT,
  },
}, {
  tableName: "Company", 
  timestamps: false,
  indexes: [
    {
      unique: true,
      fields: ['name', 'ticker', 'year', 'statement_type', 'metric']
    }
  ]
});
