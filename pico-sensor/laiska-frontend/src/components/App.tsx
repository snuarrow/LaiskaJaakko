import '../App.css'
import ToggleLed from './ToggleLed';
import ChartContainer from './ChartContainer';

function App() {
  return (
    <>
      <div style={{ width: '100%', margin: 'auto', paddingTop: '0px', paddingRight: '100px' }}>
        <h2>LaiskaJaakko Yöperho v0.7</h2>
        <ToggleLed />
        <ChartContainer />
      </div>
    </>
  )
}

export default App
