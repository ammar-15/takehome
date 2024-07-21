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

export default function CompiledTable({
  data,
}: CompiledTableProps) {
  const [rows, setRows] = useState<Row[]>([]);
  const [columns, setColumns] = useState<string[]>([]);

  useEffect(() => {
    if (!data) return;

    const filteredData = data.filter((d) => d.statement_type !== "Historical");

    const years = [...new Set(filteredData.map((d) => d.year))]
      .sort()
      .map(String);

    const grouped: { [label: string]: { [year: string]: number | string } } = {};

    for (const entry of filteredData) {
      const label = `${entry.statement_type}: ${entry.metric}`;
      if (!grouped[label]) grouped[label] = {};
      grouped[label][entry.year] = entry.value;
    }

    setColumns(years);

    const nonEmptyRows = Object.entries(grouped)
      .map(([label, valMap]) => {
        const dataArray = years.map((y) => valMap[y] ?? "-");

        // Check if all values are empty, 0, "0", "-", or ""
        const allEmpty = dataArray.every(
          (val) =>
            val === "-" ||
            val === "" ||
            val === 0 ||
            val === "0" ||
            val === null
        );

        return allEmpty ? null : { label, data: dataArray };
      })
      .filter(Boolean) as Row[];

    setRows(nonEmptyRows);
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
        {rows.map((row, i) => (
          <TableRow key={i}>
            <TableCell>{row.label}</TableCell>
            {row.data.map((val, j) => (
              <TableCell key={j}>{val}</TableCell>
            ))}
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
