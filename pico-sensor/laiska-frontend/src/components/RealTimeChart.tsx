import { useState, useEffect } from 'react';
import { Line } from 'react-chartjs-2';
import { Chart as ChartJS, registerables } from 'chart.js';
import { ChartOptions } from 'chart.js';
import 'chartjs-adapter-date-fns';

ChartJS.register(...registerables);

type RealTimeChartProps = {
  chartLabel: string;
  sensorIndex: number;
  min: number;
  max: number;
};

export default function RealTimeChart({chartLabel, sensorIndex, min, max}: RealTimeChartProps) {
  let initial_fetch_done = false;
  const [chartData, setChartData] = useState({
    labels: [],
    datasets: [
      {
        label: chartLabel,
        data: [],
      },
    ],
  });
  const [chartOptions, setChartOptions] = useState<ChartOptions<'line'>>({
    scales: {
      y: {
        type: 'linear',
        min: min,
        max: max,
      },
    }
  });
  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await fetch('http://localhost:5123/api/v1/sensor_data?sensor_index='+sensorIndex); // Fetch data from your local server
        const data = await response.json();
        const dateTimes = data.times.map((ts: number) => ts * 1000).map((ts: number) => new Date(ts).toLocaleTimeString());
        setChartData(() => ({
          labels: dateTimes,
          datasets: [
            {
              label: data.name,
              data: data.values,
            },
          ],
        }));
        setChartOptions(() => ({
          scales: {
            y: {
              type: 'linear',
              min: min,
              max: max,
            },
          }
        }));
      } catch (error) {
        console.error('Error fetching data:', error);
      }
    };
    if (initial_fetch_done === false) {
      initial_fetch_done = true;
      fetchData();
    }
    const interval = setInterval(() => {
      fetchData();
    }, 60000);
    return () => clearInterval(interval);
  }, []);
  return <Line data={chartData} options={chartOptions}/>;
};
