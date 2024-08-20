import {useState, useEffect} from 'react';
import RealTimeChart from './RealTimeChart';

type SensorMeta = {
    name: string;
    index: number;
    min: number;
    max: number;
}

export default function ChartContainer() {
    const [data, setData] = useState<SensorMeta[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    useEffect(() => {
        fetch('http://localhost:5123/api/v1/sensor_meta')
            .then(response => response.json())
            .then(data => {
                setData(data);
                setLoading(false);
            })
            .catch((error) => {
                setError(error);
                setLoading(false);
            });
    }, []);
    if (loading) return <div>Loading...</div>;
    if (error) return <div>Error: {error}</div>;

    return (
        <div>
            {(() => {
                const elements: React.ReactNode[] = [];
                data.forEach((item, index) => {
                    elements.push(
                        <RealTimeChart key={index} chartLabel={item.name} sensorIndex={item.index} min={item.min} max={item.max}/>
                    );
                });
                return elements;
            })()}
        </div>
    );
};
