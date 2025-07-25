import express from "express";
import { Company } from "../models/Company";
import { CompanyMetadata } from "../models/CompanyMetadata";

const router = express.Router();

router.get("/:ticker", async (req, res) => {
  const { ticker } = req.params;

  try {
    const all = await CompanyMetadata.findAll();
    console.log(
      " All metadata rows:",
      all.map((r) => r.toJSON())
    );
    const meta = await CompanyMetadata.findOne({ where: { ticker } });

    if (!meta) {
      return res
        .status(404)
        .json({ error: `Ticker ${ticker} not found in CompanyMetadata` });
    }

    const records = await Company.findAll({
      where: { ticker },
      order: [["year", "ASC"]],
    });

    const result = records.map((row: any) => ({
      year: row.year,
      statement_type: row.statement_type,
      metric: row.metric,
      value: row.value,
    }));

    return res.json({ source: "db", data: result });
  } catch (err) {
    console.error(" DB error:", err);
    return res.status(500).json({ error: "Server error", details: err });
  }
});

router.get("/:ticker/meta", async (req, res) => {
  const { ticker } = req.params;

  try {
    const meta = await CompanyMetadata.findOne({ where: { ticker } });

    if (!meta) {
      return res
        .status(404)
        .json({ error: `Ticker ${ticker} not found in CompanyMetadata` });
    }

    return res.json(meta.toJSON());
  } catch (err) {
    console.error("Metadata fetch error:", err);
    return res.status(500).json({ error: "Server error", details: err });
  }
});


export default router;
