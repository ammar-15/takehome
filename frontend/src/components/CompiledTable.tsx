import React from "react";
import { useEffect, useState } from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

type Row = {
  label: string;
  data: (string | number)[];
};

type CompiledTableProps = {
  ticker: string;
  data: any[] | null;
};

export default function CompiledTable({ data }: CompiledTableProps) {
  const [rows, setRows] = useState<{ section: string; rows: Row[] }[]>([]);
  const [columns, setColumns] = useState<string[]>([]);

  useEffect(() => {
    if (!data) return;

    const filteredData = data.filter((d) => d.statement_type !== "Historical");

    const years = [...new Set(filteredData.map((d) => d.year))]
      .sort((a, b) => {
        if (a === 2024) return -1;
        if (b === 2024) return 1;
        return b - a;
      })
      .map(String);

    setColumns(years);

    const grouped: {
      [statementType: string]: {
        [metric: string]: { [year: string]: number | string };
      };
    } = {};

    for (const entry of filteredData) {
      const { statement_type: statement, metric, year, value } = entry;

      if (!grouped[statement]) grouped[statement] = {};
      if (!grouped[statement][metric]) grouped[statement][metric] = {};
      grouped[statement][metric][year] = value;
    }

    const sectionedRows: { section: string; rows: Row[] }[] = [];

    for (const [statementType, metricsMap] of Object.entries(grouped)) {
      const rowsInSection: Row[] = Object.entries(metricsMap)
        .map(([metric, valMap]) => {
          const dataArray = years.map((y) => {
            const val = valMap[y];
            return typeof val === "number" ? (val / 1_000_000).toFixed(2) : "-";
          });

          const allEmpty = dataArray.every(
            (val) => val === "-" || val === "" || val === "0" || val === "0.00"
          );

          return allEmpty ? null : { label: metric, data: dataArray };
        })
        .filter(Boolean) as Row[];

      if (rowsInSection.length > 0) {
        sectionedRows.push({ section: statementType, rows: rowsInSection });
      }
    }

    setRows(sectionedRows);
  }, [data]);

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Metric</TableHead>
          {columns.map((col) => (
            <TableHead key={col}>{col}</TableHead>
          ))}
        </TableRow>
      </TableHeader>
      <TableBody>
        {rows.map((section, i) => (
          <React.Fragment key={i}>
            <TableRow>
              <TableCell
                colSpan={columns.length + 1}
                className="font-bold text-slate-700 bg-slate-100"
              >
                {section.section}
              </TableCell>
            </TableRow>
            {section.rows.map((row, j) => (
              <TableRow key={j}>
                <TableCell>{row.label}</TableCell>
                {row.data.map((val, k) => (
                  <TableCell key={k}>{val}</TableCell>
                ))}
              </TableRow>
            ))}
          </React.Fragment>
        ))}
      </TableBody>
    </Table>
  );
}
