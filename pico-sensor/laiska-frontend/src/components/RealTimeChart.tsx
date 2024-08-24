import { useState, useEffect } from "react";
import { Line } from "react-chartjs-2";
import { Chart as ChartJS, registerables } from "chart.js";
import { ChartOptions, TimeScaleOptions } from "chart.js";
import "chartjs-adapter-date-fns";
import { API_URL } from "../config";
import axios from "axios";

ChartJS.register(...registerables);

type RealTimeChartProps = {
  //chartLabel: string;
  sensorIndex: number;
  min: number;
  max: number;
};

const xAxisOptions: Partial<TimeScaleOptions> = {
  type: "time",
  // @ts-expect-error // This is a bug in the type definitions
  time: {
    unit: "hour",
    displayFormats: {
      hour: "HH",
    },
  },
  // @ts-expect-error // This is a bug in the type definitions
  ticks: {
    maxTicksLimit: 7,
  },
  grid: {
    color: 'rgba(255, 255, 255, 0.1)', // x-axis grid line color
  }
};

export default function RealTimeChart({
  sensorIndex,
  min,
  max,
}: RealTimeChartProps) {
  let initial_fetch_done = false;
  const [chartData, setChartData] = useState({
    labels: [],
    datasets: [
      {
        label: "Loading...",
        data: [],
        pointRadius: 2,
      },
    ],
  });
  const [chartOptions, setChartOptions] = useState<ChartOptions<"line">>({
    scales: {
      y: {
        type: "linear",
        min: min,
        max: max,
        grid: {
          color: 'rgba(255, 255, 255, 0.1)', // x-axis grid line color
        }
      },
      x: xAxisOptions,
    },
  });
  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await axios.get(
          API_URL + "/api/v1/sensor_data?sensor_index=" + sensorIndex,
        );
        const dateTimes = response.data.times
          .map((ts: number) => ts * 1000)
          .map((ts: number) => new Date(ts));
        const label =
          response.data.type === "MH-Moisture"
            ? "Soil Moisture " + sensorIndex + ": " + response.data.name
            : response.data.name;
        setChartData(() => ({
          labels: dateTimes,
          datasets: [
            {
              label: label,
              data: response.data.values,
              pointRadius: 2,
            },
          ],
        }));
        setChartOptions(() => ({
          scales: {
            y: {
              type: "linear",
              min: min,
              max: max,
              grid: {
                color: 'rgba(255, 255, 255, 0.1)', // x-axis grid line color
              }
            },
            x: xAxisOptions,
          },
        }));
      } catch (error) {
        console.error("Error fetching data:", error);
      }
    };
    if (initial_fetch_done === false) {
      initial_fetch_done = true;
      setTimeout(() => {
        fetchData();
      }, 500 * sensorIndex); // Delay the initial fetch to avoid overloading the microcontroller
    }
    const interval = setInterval(() => {
      fetchData();
    }, 60000);
    return () => clearInterval(interval);
  }, []);
  return <Line data={chartData} options={chartOptions} />;
}
