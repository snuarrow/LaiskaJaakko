import '../App.css'
import ToggleButton from './ToggleButton';
import ChartContainer from './ChartContainer';

function App() {
  return (
    <>
      <div style={{ width: '100%', margin: 'auto', paddingTop: '0px', paddingRight: '100px' }}>
        <h2>LaiskaJaakko Yöperho v0.7</h2>
        <ToggleButton />
        <ChartContainer />
      </div>
    </>
  )
}

export default App
