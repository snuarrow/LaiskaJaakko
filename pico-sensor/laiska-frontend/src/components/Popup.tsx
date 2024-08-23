import React, {useState, useEffect} from 'react';
import axios from 'axios';
import PlantNameEdit from './PlantNameEdit';
import { API_URL } from '../config';

interface PopupProps {
  isOpen: boolean;
}

type SensorMeta = {
    name: string;
    index: number;
    type: string;
}

export default function Popup({ isOpen: isOpen }: PopupProps) {
    if (!isOpen) return null;

    const handleReload = () => {
        window.location.reload();
    };

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
        <div className="popup-overlay">
            <div className="popup-content">
                <button className="popup-close" onClick={handleReload}>×</button>
                <h2>Edit plant names:</h2>
                {(() => {
                    const elements: React.ReactNode[] = [];
                    data.forEach((item, index) => {
                        if (item.type === "MH-Moisture") {
                            elements.push(
                                <PlantNameEdit key={index} sensorName={item.name} sensorIndex={item.index}/>
                            );
                        }
                    });
                    return elements;
                })()}
            </div>
        </div>
  );
};
