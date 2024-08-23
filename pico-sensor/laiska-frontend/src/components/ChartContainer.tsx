import {useState, useEffect} from 'react';
import RealTimeChart from './RealTimeChart';
import { API_URL } from '../config';
import axios from 'axios';

type SensorMeta = {
    name: string;
    index: number;
    min: number;
    max: number;
}

export default function ChartContainer() {
    const [data, setData] = useState<SensorMeta[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchSensorMeta = async () => {
            try {
                const response = await axios.get(API_URL+'/api/v1/sensor_meta');
                setData(response.data);
                setLoading(false);
            } catch (error) {
                console.error('Error fetching sensor meta:', error);
                setLoading(false);
            }
        };
        fetchSensorMeta();
    }, []);
    if (loading) return <div>Loading...</div>;

    return (
        <div>
            {(() => {
                const elements: React.ReactNode[] = [];
                data.forEach((item, index) => {
                    elements.push(
                        <RealTimeChart key={index} sensorIndex={item.index} min={item.min} max={item.max}/>
                    );
                });
                return elements;
            })()}
        </div>
    );
};
